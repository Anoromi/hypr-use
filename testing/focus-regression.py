"""Same-desktop regression: stop on observed foreground transfer to test windows."""
import os,sys,json,time,socket,threading,subprocess,importlib.util,shlex,signal
from pathlib import Path
r=Path(__file__).resolve().parent
if os.environ.get('HYPR_FOCUS_TEST')!='1':
 e=json.load(open(r/'live-session/env.json'))
 for k in ['HYPRLAND_INSTANCE_SIGNATURE','WAYLAND_DISPLAY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS']:
  if os.environ.get(k):e[k]=os.environ[k]
 e.update(HYPR_FOCUS_TEST='1',HYPR_AGENT_PORTAL_PERMISSION_MODE='full',HYPR_AGENT_PORTAL_APP_POLICIES='hypr-use-focus-test=full',HYPR_AGENT_PORTAL_CONFINE='class:hypr-use-focus-test',HYPR_AGENT_PORTAL_CLIPBOARD='none');e['PATH']=str(r/'runtime-result/bin')+':'+e['PATH'];os.execve(str(r/'runtime-result/bin/python3'),['python3',__file__],e)
out=r/'focus-regressions'/time.strftime('%Y%m%d-%H%M%S');out.mkdir(parents=True)
def ctl(*args):return json.loads(subprocess.check_output(['hyprctl','-j',*args],text=True))
baseline=ctl('activewindow');assert baseline.get('address') and baseline.get('class')!='hypr-use-focus-test'
assert not any(w['class']=='hypr-use-focus-test' for w in ctl('clients')),'Existing test window; refusing ambiguous ownership'
spec=importlib.util.spec_from_file_location('focus_detector',r/'focus-detector.py');detector_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(detector_module);detector=detector_module.FocusDetector(baseline['address'])
workspace=next(n for n in range(901,1000) if n not in {w['id'] for w in ctl('workspaces')})
state={'stage':'baseline','targets':set(),'events':[],'violations':[],'stop':False};lock=threading.Lock();trigger=threading.Event();target_pids=set()
def record(kind,data):
 with lock:
  row={'wall_time':time.time(),'monotonic_ns':time.monotonic_ns(),'stage':state['stage'],'kind':kind,'data':data};state['events'].append(row)
  with (out/'focus-events.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
  return row
def violation(address,source):
 detector.targets.update(state['targets'])
 if detector.observe(address) and not trigger.is_set():
  row=record('refocus',{'address':address,'source':source});state['violations'].append(row);trigger.set()
  # Abort our disposable fixture immediately rather than waiting for an
  # in-flight screenshot/AT-SPI observation to finish.
  for pid in list(target_pids):
   try:
    if str(r/'focus-regression-fixture.py').encode() in Path(f'/proc/{pid}/cmdline').read_bytes():os.kill(pid,signal.SIGTERM)
   except (FileNotFoundError,ProcessLookupError):pass
sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);sock.connect(os.environ['XDG_RUNTIME_DIR']+'/hypr/'+os.environ['HYPRLAND_INSTANCE_SIGNATURE']+'/.socket2.sock');sock.settimeout(.2)
def events():
 pending='';active=baseline['address']
 while not state['stop']:
  try:data=sock.recv(65536)
  except socket.timeout:continue
  except OSError as exc:
   if not state['stop']:record('observer-error',str(exc));trigger.set()
   return
  if not data:
   if not state['stop']:record('observer-error','Hyprland event socket closed');trigger.set()
   return
  pending+=data.decode(errors='replace')
  while '\n' in pending:
   line,pending=pending.split('\n',1);name,_,value=line.partition('>>')
   if name=='openwindow':
    fields=value.split(',',3)
    if len(fields)>=3 and fields[2]=='hypr-use-focus-test':
     address='0x'+fields[0].removeprefix('0x');state['targets'].add(address);record(name,{'address':address,'workspace':fields[1],'class':fields[2]});violation(active,'openwindow-after-active')
   elif name=='activewindowv2':
    active='0x'+value.removeprefix('0x') if value else '';record(name,{'address':active});violation(active,'socket2')
   elif name in ['workspacev2','movewindowv2','closewindow']:record(name,value)
def poll():
 while not state['stop']:
  try:
   w=ctl('activewindow')
   if w.get('class')=='hypr-use-focus-test':state['targets'].add(w['address']);target_pids.add(w['pid']);violation(w['address'],'poll')
   violation(w.get('address',''),'poll')
   record('sample',{'address':w.get('address'),'class':w.get('class'),'workspace':w.get('workspace',{}).get('id')})
  except Exception as e:record('observer-error',str(e));trigger.set()
  time.sleep(.1)
threads=[threading.Thread(target=fn,daemon=True) for fn in [events,poll]]
for t in threads:t.start()
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
m=load('focus_portal',r.parent/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py');m.ensure_session_environment();load('focus_timing',r/'portal-timing.py').install(m)
results=[];error=None;checks=[]
def stage(name):
 if trigger.is_set():raise RuntimeError('Focus guard stopped further actions')
 state['stage']=name;record('stage-start',name)
def call(name,args):
 stage(name);req={'jsonrpc':'2.0','id':len(results)+1,'method':'tools/call','params':{'name':name,'arguments':args}};res=m.handle(req);results.append({'request':req,'response':res});(out/'tools.json').write_text(json.dumps(results));record('stage-end',name)
 if trigger.is_set():raise RuntimeError('Refocus observed during '+name)
 if res.get('result',{}).get('isError'):raise RuntimeError(str(res['result']['content'])[:1000])
 return res['result'].get('structuredContent',{})
try:
 stage('launch');cmd=shlex.join(['env','GDK_BACKEND=wayland','GTK_MODULES=gail:atk-bridge','NO_AT_BRIDGE=0',*['%s=%s'%(k,os.environ[k]) for k in ['GI_TYPELIB_PATH','XDG_DATA_DIRS','WAYLAND_DISPLAY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS'] if k in os.environ],str(r/'runtime-result/bin/python3'),str(r/'focus-regression-fixture.py'),str(out/'fixture-state.json')]);launch_result=m.hyprctl_exec(f'[workspace {workspace} silent] '+cmd+' > '+shlex.quote(str(out/'fixture.log'))+' 2>&1');record('launch-result',launch_result)
 for _ in range(100):
  ws=[w for w in ctl('clients') if w['class']=='hypr-use-focus-test']
  if ws or trigger.is_set():break
  time.sleep(.1)
 assert ws,'Fixture did not map'
 for w in ws:state['targets'].add(w['address']);target_pids.add(w['pid'])
 if trigger.is_set():raise RuntimeError('Refocus during launch')
 assert all(w['workspace']['id']==workspace for w in ws),'Fixture mapped on wrong workspace'
 app=m.window_selector(ws[0]);s=call('get_app_state',{'app':app})
 s=call('type_text',{'app':app,'text':'background-focus-test','method':'keys'})
 checks.append({'stage':'typing','ok':json.load(open(out/'fixture-state.json'))['text']=='background-focus-test'})
 s=call('press_key',{'app':app,'key':'ctrl+a'})
 s=call('type_text',{'app':app,'text':'verified','method':'keys'})
 checks.append({'stage':'replace-selection','ok':json.load(open(out/'fixture-state.json'))['text']=='verified'})
 e=next(e for e in s['elements'] if e.get('name')=='Open test dialog');s=call('click',{'app':app,'element_index':e['index'],'element_click_mode':'atspi'})
 checks.append({'stage':'popup-open','ok':json.load(open(out/'fixture-state.json'))['popup_open']})
 ws=[w for w in ctl('clients') if w['class']=='hypr-use-focus-test']
 for w in ws:state['targets'].add(w['address']);target_pids.add(w['pid'])
 dialog=next(w for w in ws if w['title']=='Background test dialog');d=m.window_selector(dialog);s=call('get_app_state',{'app':d});e=next(e for e in s['elements'] if e.get('name')=='Close test dialog');call('click',{'app':d,'element_index':e['index'],'element_click_mode':'atspi'})
 checks.append({'stage':'popup-close','ok':not json.load(open(out/'fixture-state.json'))['popup_open']})
 stage('settling');trigger.wait(1)
except Exception as exc:error=str(exc)
finally:
 state['stage']='cleanup'
 for w in ctl('clients'):
  if w['class']=='hypr-use-focus-test':target_pids.add(w['pid'])
 for pid in target_pids:
  try:
   if str(r/'focus-regression-fixture.py').encode() in Path(f'/proc/{pid}/cmdline').read_bytes():os.kill(pid,signal.SIGTERM)
  except (FileNotFoundError,ProcessLookupError):pass
 time.sleep(.3);final=ctl('activewindow');state['stop']=True;sock.close()
 for t in threads:t.join(timeout=1)
 summary={'baseline':{'address':baseline['address'],'class':baseline['class'],'workspace':baseline['workspace']['id']},'workspace':workspace,'refocus_events':state['violations'],'checks':checks,'calls':len(results),'error':error,'final':{'address':final.get('address'),'class':final.get('class'),'workspace':final.get('workspace',{}).get('id')},'passed':not error and not state['violations'] and all(x['ok'] for x in checks),'definition':'Foreground changes to an agent-owned window. Switching among unrelated user windows is not a failure.'};(out/'summary.json').write_text(json.dumps(summary,indent=2));print(out);print(json.dumps(summary,indent=2))
