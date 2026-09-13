"""Compare native popup input routes on fresh owned GTK fixtures."""
import base64,hashlib,json,os,shlex,signal,subprocess,sys,time
from pathlib import Path
here=Path(__file__).resolve().parent;root=here.parents[1];old=here.parent/'unified-benchmark'
sys.path.insert(0,str(old))
from monitor import Monitor,ctl
from native_runtime import native_runtime
app='hypr-use-bench';out=here/'diagnostics'/sys.argv[1];out.mkdir(parents=True,exist_ok=False)
cases=sys.argv[2:] or ['pointer-legacy','pointer-cached','semantic-cached']
files=[*root.joinpath('mcp/unified').glob('*.py'),*root.joinpath('mcp/unified').glob('*.mjs'),*root.joinpath('vendor/hypr-agent-portal-0.56.2/mcp').glob('*.py'),Path(__file__),old/'fixture.py',old/'monitor.py',here/'launch_owned.py']
def hashes():return {(str(p.relative_to(root)) if p.is_relative_to(root) else str(p)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
native=native_runtime(root)
files += [here/'native_runtime.py',root/'testing/live-session/active-plugin.json',Path(native['path'])]
source_hashes=hashes();(out/'manifest.json').write_text(json.dumps({'native_runtime':native,'cases':cases,'source_hashes':source_hashes},indent=2))
assert not any(w['class']==app for w in ctl('clients'))
m=Monitor(out/'focus.jsonl',[app]);owned=None;server=None;rows=[]
def stop():
 if server and server.poll() is None:os.killpg(server.pid,signal.SIGTERM)
 if owned:
  try:
   fields=Path(f"/proc/{owned['pid']}/stat").read_text().split(') ',1)[1].split()
   if fields[19]==owned['start']:os.killpg(owned['pid'],signal.SIGTERM)
  except (ProcessLookupError,FileNotFoundError):pass
m.callback=stop
rule='hl.window_rule({name="hypr-use-native-choice-probe",match={class="^hypr-use-bench$"},no_initial_focus=true,suppress_event="activate activatefocus",workspace="902 silent"}):set_enabled(true)'
try:
 for case in cases:
  assert hashes()==source_hashes and not m.trigger.is_set();m.stage=case;d=out/case;d.mkdir();f=d/'fixture';f.mkdir()
  env={k:v for k,v in os.environ.items() if not k.startswith(('HYPR_USE_','HYPR_AGENT_PORTAL_'))}
  saved=json.loads((root/'testing/live-session/env.json').read_text());env.update({k:saved[k] for k in ['GI_TYPELIB_PATH','XDG_DATA_DIRS'] if saved.get(k)})
  env.update(GTK_MODULES='gail:atk-bridge',GDK_BACKEND='wayland',NO_AT_BRIDGE='0')
  cmd=[str(root/'testing/runtime-result/bin/python3'),str(old/'fixture.py'),str(f),'0']
  (d/'launch.json').write_text(json.dumps({'command':cmd,'env':{k:env[k] for k in ['GI_TYPELIB_PATH','XDG_DATA_DIRS','GTK_MODULES','GDK_BACKEND','NO_AT_BRIDGE'] if k in env}}))
  assert subprocess.check_output(['hyprctl','eval',rule],text=True).strip()=='ok'
  launch='[workspace 902 silent] '+shlex.join([sys.executable,str(here/'launch_owned.py'),str(d/'launch.json')])+' > '+shlex.quote(str(d/'app.log'))+' 2>&1'
  assert subprocess.check_output(['hyprctl','eval','hl.dispatch(hl.dsp.exec_cmd('+json.dumps(launch)+'))'],text=True).strip()=='ok'
  for _ in range(150):
   if (d/'owned-process.json').exists():owned=json.loads((d/'owned-process.json').read_text())
   windows=[w for w in ctl('clients') if w['class']==app]
   if windows and (f/'state.json').exists():break
   assert not m.trigger.is_set();time.sleep(.03)
  assert owned and windows and all(w['workspace']['id']==902 for w in windows)
  assert json.loads((f/'state.json').read_text()).get('Country')!='Germany'
  env.update(HYPR_AGENT_PORTAL_PERMISSION_MODE='full',HYPR_AGENT_PORTAL_APPROVAL_POLICY='never',HYPR_AGENT_PORTAL_CONFINE='class:'+app,HYPR_USE_WIRE_LOG=str(d/'wire.jsonl'),HYPR_USE_PORTAL_LOG=str(d/'portal.jsonl'),HYPR_USE_AX_BYTECODE='0' if 'legacy' in case else '1')
  server=subprocess.Popen(['node',str(root/'mcp/unified/server.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(d/'stderr.log').open('w'),text=True,env=env,start_new_session=True)
  steps=[]
  def js(code):
   assert not m.trigger.is_set();start=time.monotonic();server.stdin.write(json.dumps({'jsonrpc':'2.0','id':len(steps)+1,'method':'tools/call','params':{'name':'js','arguments':{'code':code}}})+'\n');server.stdin.flush()
   r=json.loads(server.stdout.readline());steps.append({'code':code,'seconds':time.monotonic()-start,'error':r['result'].get('isError')});(d/f'response-{len(steps)}.json').write_text(json.dumps(r));return r
  def state():return json.loads((d/'portal.jsonl').read_text().splitlines()[-1])['response']['result']['structuredContent']
  js("var app=await cua.getApp('hypr-use-bench');")
  if case.startswith('workflow'):
   js("await app.selectOptions({choices:[{name:'Country',option:'Germany'}]});")
   js("await app.selectOptions({choices:[{name:'Country',option:'Germany'}]});")
  else:
   country=next(e for e in state()['elements'] if e['name']=='Country' and e['controlType']=='combo box')
   js(f"await app.click({country['index']}); await app.getAXState();")
   if '-image-' in case:
    captured=js('await app.getAXStateAndScreenshot();')
    for block in captured['result']['content']:
     if block.get('type')=='image':(d/'popup.png').write_bytes(base64.b64decode(block['data']))
   germany=next(e for e in state()['elements'] if e['name']=='Germany' and e['controlType']=='menu item')
   if 'inspect' in case:
    frame=germany['frame'];payload=f"{state()['target']},{frame['x']+frame['width']/2},{frame['y']+frame['height']/2},inspect"
    inspected=subprocess.run(['hyprctl','eval','local result=hl.dispatch(hl.plugin.hypr_agent_portal.pointer_relative('+json.dumps(payload)+')); error(result.error or "missing inspection")'],capture_output=True,text=True)
    (d/'surface-inspect.txt').write_text(inspected.stdout+inspected.stderr)
   if case.startswith('semantic'):code=f"await app.performSecondaryAction({germany['index']},'click');"
   elif case.startswith('keyboard'):code="await app.pressKey('End Return');"
   else:code=f"await app.click({germany['index']});"
   js(code+'await app.getAXState();');time.sleep(.15)
  actual=json.loads((f/'state.json').read_text());row={'case':case,'passed':actual.get('Country')=='Germany' and not any(s['error'] for s in steps),'state':actual,'steps':steps,'refocus':bool(m.violations)};rows.append(row);print(json.dumps(row),flush=True)
  server.stdin.close();server.wait(timeout=10);server=None;stop();owned=None
  for _ in range(100):
   if not any(w['class']==app for w in ctl('clients')):break
   time.sleep(.03)
finally:
 stop();m.close();subprocess.run(['hyprctl','eval','hl.window_rule({name="hypr-use-native-choice-probe",match={class="^hypr-use-bench$"}}):set_enabled(false)'],capture_output=True)
 (out/'results.json').write_text(json.dumps({'cases':rows,'refocus':m.violations,'source_unchanged':hashes()==source_hashes,'completed_all':len(rows)==len(cases),'error':str(sys.exc_info()[1]) if sys.exc_info()[1] else None},indent=2))
