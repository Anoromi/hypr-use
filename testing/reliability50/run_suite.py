"""Independent desktop fixtures, fresh Astra CLI instances, controller-only grading."""
import hashlib,json,os,signal,socket,subprocess,sys,tempfile,time,urllib.request,shlex
from pathlib import Path
here=Path(__file__).resolve().parent;root=here.parents[1];old=here.parent/'unified-benchmark'
sys.path.insert(0,str(old))
from monitor import Monitor,ctl
from catalog import catalog
from web_fixture import Fixture
import odf
phase=sys.argv[1];selected=set(sys.argv[2:]);out=here/'runs'/phase;out.mkdir(parents=True,exist_ok=True)
source_files=list((root/'mcp/unified').glob('*.py'))+list((root/'mcp/unified').glob('*.mjs'))+[root/'vendor/hypr-agent-portal-0.56.2/scripts/hypr-agent-portalctl',root/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py',*[here/name for name in ['run_suite.py','catalog.py','web_fixture.py','odf.py','launch_owned.py']],here/'cdp.mjs',old/'run.py']
source_files += list((root/'vendor/hypr-agent-portal-0.56.2/mcp').glob('*.py'))
def hashes():return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
manifest={'model':'gpt-6-astra','effort':'xhigh','source_hashes':hashes(),'catalog':catalog(),'started_at':time.time(),'policy':'Fresh profiles and agent cwd; no retries replace original outcomes; no restore preflight; all GUI actions through JS MCP. Controller prep/grading uses files or CDP. Stop on refocus.'}
if (out/'manifest.json').exists():
 manifest=json.loads((out/'manifest.json').read_text());assert manifest['source_hashes']==hashes(),'Source changed; use a new phase'
else:(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
classes=['hypr-use-bench','hypr-use-r50-browser','libreoffice-calc','libreoffice-writer','libreoffice-startcenter','soffice']
assert not any(w['class'] in classes for w in ctl('clients')),'A target app already exists; refusing to touch it'
monitor=Monitor(out/f'focus-{time.time_ns()}.jsonl',classes)
rule='hl.window_rule({name="hypr-use-r50",match={class="^(hypr-use-bench|hypr-use-r50-browser|libreoffice.*|soffice)$"},no_initial_focus=true,suppress_event="activate activatefocus",workspace="902 silent"}):set_enabled(true)'
assert subprocess.check_output(['hyprctl','eval',rule],text=True).strip()=='ok'
env=os.environ.copy()
for k in list(env):
 if k.startswith(('HYPR_USE_','HYPR_AGENT_PORTAL_')):env.pop(k)
saved=json.loads((root/'testing/live-session/env.json').read_text())
appenv=env.copy()
for k in ['GI_TYPELIB_PATH','XDG_DATA_DIRS']:
 if saved.get(k):appenv[k]=saved[k]
appenv.update(GDK_BACKEND='wayland',GTK_MODULES='gail:atk-bridge',NO_AT_BRIDGE='0',SAL_USE_VCLPLUGIN='gtk3',SAL_DISABLE_OPENCL='1')
active_process=None;agent_process=None

def stop():
 for p in [agent_process,active_process]:
  if p and p.poll() is None:
   try:os.killpg(p.pid,signal.SIGTERM)
   except ProcessLookupError:pass
monitor.callback=stop

def pages(port):return [p for p in json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list',timeout=3)) if p['type']=='page']
def cdp(page,method,args={}):return json.loads(subprocess.check_output(['node',str(here/'cdp.mjs'),page['webSocketDebuggerUrl'],method,json.dumps(args)],text=True,timeout=15))
def grade(task,d,fixture=None,port=None):
 group=task['group'];check=task['check'];final=(d/task['id']/'final.txt').read_text() if (d/task['id']/'final.txt').exists() else ''
 if group=='native':
  actual=json.loads((d/'fixture/state.json').read_text());checks={k:actual.get(k)==v for k,v in check.items()};return {'passed':all(checks.values()),'checks':checks,'evidence':actual}
 if group in ['calc','writer']:return odf.inspect(d/('document.ods' if group=='calc' else 'document.odt'),group,check)
 if group=='web':
  actual=fixture.state.copy();checks={k:actual.get(k)==v for k,v in check.items()};return {'passed':all(checks.values()),'checks':checks,'evidence':actual}
 ps=pages(port);urls=[p['url'] for p in ps];checks={};evidence={'urls':urls,'visited':fixture.visited}
 if 'url_contains' in check:checks['url']=any(check['url_contains'] in u for u in urls)
 if 'answer' in check:checks['answer']=check['answer'].lower() in final.lower()
 if 'path' in check:checks['path']=any(urllib.parse.urlparse(u).path==check['path'] for u in urls)
 if 'visited' in check:checks['visited']=check['visited'] in fixture.visited
 if 'tabs' in check:checks['tabs']=sorted(urllib.parse.urlparse(u).path for u in urls)==sorted(check['tabs'])
 if 'scrolled' in check:
  positions=[cdp(p,'Runtime.evaluate',{'expression':'window.scrollY','returnByValue':True}) for p in ps];evidence['scroll']=positions;checks['scrolled']=any(p.get('result',{}).get('result',{}).get('value',0)>1000 for p in positions)
 return {'passed':bool(checks) and all(checks.values()),'checks':checks,'evidence':evidence}
class OwnedProcess:
 def __init__(self,record):self.pid=record['pid'];self.start=record['start']
 def poll(self):
  try:
   fields=Path(f'/proc/{self.pid}/stat').read_text().split(') ',1)[1].split()
   return 0 if fields[19]!=self.start or fields[0]=='Z' else None
  except FileNotFoundError:return 0
 def wait(self,timeout=10):
  end=time.monotonic()+timeout
  while self.poll() is None:
   if time.monotonic()>end:raise subprocess.TimeoutExpired('owned app',timeout)
   time.sleep(.05)
  return 0

results=[]
try:
 for task in catalog():
  if selected and task['id'] not in selected:continue
  d=out/task['id']
  if (d/'summary.json').exists():results.append(json.loads((d/'summary.json').read_text()));continue
  d.mkdir(exist_ok=True);monitor.stage=task['id'];fixture=None;port=None;active_process=None;agent_process=None;started=time.time();row={'id':task['id'],'group':task['group']}
  try:
   assert not monitor.trigger.is_set(),'Focus monitor halted suite'
   if task['group']=='native':
    f=d/'fixture';f.mkdir();
    if task.get('saved_note'):(f/'note.txt').write_text(task['saved_note'])
    app='hypr-use-bench';cmd=[str(root/'testing/runtime-result/bin/python3'),str(old/'fixture.py'),str(f),str(task.get('delay_ms',0))]
   elif task['group'] in ['navigation','web']:
    fixture=Fixture();app='hypr-use-r50-browser'
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    urls=[f'http://127.0.0.1:{fixture.port}/'+('web' if task['group']=='web' else 'start')]
    if task.get('closed_tab'):urls += [f'http://127.0.0.1:{fixture.port}/second',f'http://127.0.0.1:{fixture.port}/third']
    cmd=['chromium','--user-data-dir='+str(d/'browser-profile'),'--class='+app,'--ozone-platform=wayland','--force-renderer-accessibility','--no-first-run','--no-default-browser-check','--remote-debugging-address=127.0.0.1','--remote-debugging-port='+str(port),*urls]
   else:
    profile_user=d/'office-profile/user';profile_user.mkdir(parents=True)
    (profile_user/'registrymodifications.xcu').write_text('<oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Office.Common/Misc"><prop oor:name="FirstRun" oor:op="fuse"><value>false</value></prop><prop oor:name="ShowTipOfTheDay" oor:op="fuse"><value>false</value></prop></item></oor:items>')
    app='libreoffice-'+task['group'];doc=d/('document.ods' if task['group']=='calc' else 'document.odt');odf.seed(doc,task['group'],task['seed'])
    cmd=['libreoffice','-env:UserInstallation='+(d/'office-profile').as_uri(),'--norestore','--nofirststartwizard',str(doc)]
   # Reinstall the temporary rule for every launch and independently attach
   # an explicit silent-workspace exec rule. A missing temporary class rule
   # must not cause a window to map onto the user's current workspace.
   assert subprocess.check_output(['hyprctl','eval',rule],text=True).strip()=='ok'
   launch=d/'launch.json';launch.write_text(json.dumps({'command':cmd,'env':{k:appenv[k] for k in ['GDK_BACKEND','GTK_MODULES','NO_AT_BRIDGE','SAL_USE_VCLPLUGIN','SAL_DISABLE_OPENCL','GI_TYPELIB_PATH','XDG_DATA_DIRS'] if k in appenv}}))
   command='[workspace 902 silent] '+shlex.join([sys.executable,str(here/'launch_owned.py'),str(launch)])+' > '+shlex.quote(str(d/'app.log'))+' 2>&1'
   assert subprocess.check_output(['hyprctl','eval','hl.dispatch(hl.dsp.exec_cmd('+json.dumps(command)+'))'],text=True).strip()=='ok'
   for _ in range(100):
    if (d/'owned-process.json').exists():break
    time.sleep(.02)
   active_process=OwnedProcess(json.loads((d/'owned-process.json').read_text()))
   for _ in range(150):
    assert not monitor.trigger.is_set(),'Refocus during setup'
    windows=[w for w in ctl('clients') if w['class']==app]
    if windows:
     assert all(w['workspace']['id']==902 for w in windows),'Target mapped outside background workspace'
     break
    time.sleep(.2)
   else:raise RuntimeError('Target window did not appear')
   if port:
    for _ in range(60):
     try:
      ps=pages(port)
      if len(ps)==len(urls) and all(p['title'] for p in ps):break
     except Exception:pass
     time.sleep(.2)
    else:raise RuntimeError('Browser setup did not commit pages')
    if task.get('closed_tab'):
     p=next(p for p in ps if p['url'].endswith('/third'));cdp(p,'Page.getNavigationHistory');urllib.request.urlopen(f'http://127.0.0.1:{port}/json/close/'+p['id']).read();time.sleep(.3);assert len(pages(port))==2
   time.sleep(.5)
   (d/'setup.json').write_text(json.dumps({'windows':windows,'command':cmd,'port':port,'refocus':monitor.violations},indent=2))
   initial=grade(task,d,fixture,port);(d/'initial-grade.json').write_text(json.dumps(initial,indent=2));assert not initial['passed'],'Invalid task: initial state already passes evaluator'
   row['setup_s']=time.time()-started
   taskfile=d/'agent-task.json';taskfile.write_text(json.dumps([{'id':task['id'],'app':app,'prompt':task['prompt']}]))
   cwd=Path(tempfile.mkdtemp(prefix='hypr-use-r50-agent-'));(cwd/'AGENTS.md').write_text('Always be brief.\n')
   agentenv=env|{'HYPR_USE_TASK_FILE':str(taskfile),'HYPR_USE_AGENT_CWD':str(cwd),'HYPR_USE_REASONING_EFFORT':'xhigh','HYPR_USE_TASK_TIMEOUT':'240'}
   if task['group']=='writer':agentenv['HYPR_AGENT_PORTAL_CONFINE']='class:libreoffice-writer,class:soffice,class:libreoffice-startcenter'
   runnerlog=(d/'runner.log').open('w');phasepath=os.path.relpath(d,old)
   agent_process=subprocess.Popen([sys.executable,str(old/'run.py'),phasepath,task['id']],env=agentenv,stdout=runnerlog,stderr=runnerlog,start_new_session=True)
   agent_process.wait(timeout=270);runnerlog.close()
   result=json.loads((d/task['id']/'result.json').read_text());row.update(result)
   final=grade(task,d,fixture,port);(d/'grade.json').write_text(json.dumps(final,indent=2))
   row['outcome']='pass' if final['passed'] and not result['timeout'] and result['exit']==0 and not result['refocus'] else 'fail'
   events=[json.loads(l)['event'] for l in (d/task['id']/'events.jsonl').read_text().splitlines()]
   errors=[e.get('message',e.get('error',{}).get('message','')) for e in events if e.get('type') in ['error','turn.failed']]
   row['provider_errors']=errors
   row['failure_kind']='provider' if errors else ('timeout' if result['timeout'] else ('task' if row['outcome']=='fail' else None))
   row['grade_passed']=final['passed'];row['source_unchanged']=hashes()==manifest['source_hashes'];assert row['source_unchanged'],'Runtime source changed during phase'
  except Exception as exc:
   row.update(outcome='harness_error' if 'setup_s' in row else 'setup_error',error=str(exc));stop()
  finally:
   if active_process:
    # Only terminate the process group launched by this task. Never pkill by app name.
    try:os.killpg(active_process.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:active_process.wait(timeout=8)
    except subprocess.TimeoutExpired:os.killpg(active_process.pid,signal.SIGKILL);active_process.wait()
    for _ in range(40):
     if not any(w['class'] in classes for w in ctl('clients')):break
     time.sleep(.1)
   if fixture:fixture.close()
   row['refocus']=bool(monitor.violations);row['wall_s']=time.time()-started
   (d/'summary.json').write_text(json.dumps(row,indent=2));results.append(row);(out/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(row),flush=True)
  if monitor.trigger.is_set():break
  if len(results)>=3 and all(r.get('failure_kind')=='provider' for r in results[-3:]):
   print('Paused: three consecutive provider failures; remaining tasks are not attempted.',flush=True);break
finally:
 stop();subprocess.run(['hyprctl','eval','hl.window_rule({name="hypr-use-r50",match={class="^(hypr-use-bench|hypr-use-r50-browser|libreoffice.*|soffice)$"}}):set_enabled(false)'],capture_output=True)
 monitor.close();(out/'focus-summary.json').write_text(json.dumps({'violations':monitor.violations,'ended_at':time.time()},indent=2))
