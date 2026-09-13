"""Load old/new popup routing in a disposable compositor before live testing."""
import hashlib,json,os,signal,subprocess,sys,tempfile,time,threading
from pathlib import Path
here=Path(__file__).resolve().parent;root=here.parents[1];testing=root/'testing'
out=here/'diagnostics'/sys.argv[1];out.mkdir(parents=True,exist_ok=False)
runtime=Path(tempfile.mkdtemp(prefix='hp-'));processes=[];monitor_stop=threading.Event();focus=[];rows=[];mcp=None
old=(testing/'plugin-reliability-sequence-result/lib/libhypr-agent-portal.so').resolve();new=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else (testing/'plugin-popup-hit-result/lib/libhypr-agent-portal.so').resolve()
env={k:os.environ[k] for k in ['PATH','XDG_DATA_DIRS','LD_LIBRARY_PATH'] if k in os.environ}
env.update(XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(out),XDG_STATE_HOME=str(out/'state'),XDG_CACHE_HOME=str(out/'cache'),HYPRLAND_NO_SD_VARS='1',LIBSEAT_BACKEND='hypr-use-disabled',AQ_DRM_DEVICES='/nonexistent-hypr-use-device',WLR_BACKENDS='headless',WLR_RENDERER='gles2',WLR_HEADLESS_OUTPUTS='1')
def launch(name,args,stdout=None):
 p=subprocess.Popen(args,env=env,stdout=stdout or (out/(name+'.log')).open('w'),stderr=(out/(name+'.stderr')).open('w'),start_new_session=True,text=True);processes.append(p);return p
def wait_for(fn,process,seconds=15):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  if fn():return
  if process.poll() is not None:raise RuntimeError(f'Owned process {process.pid} exited: {process.returncode}')
  time.sleep(.1)
 raise RuntimeError('Private compositor/app readiness timed out')
def ctl(*args):return subprocess.check_output(['hyprctl',*args],env=env,text=True,timeout=5)
def clients():return json.loads(ctl('-j','clients'))
try:
 cage=launch('cage',[str(testing/'runtime-result/bin/cage'),'-s','--','sleep','600'])
 wait_for(lambda:bool(list(runtime.glob('wayland-*.lock'))),cage)
 parent=next(runtime.glob('wayland-*.lock')).name.removesuffix('.lock')
 bus=launch('dbus',['dbus-daemon','--session','--nofork','--print-address=1'],subprocess.PIPE);env['DBUS_SESSION_BUS_ADDRESS']=bus.stdout.readline().strip();assert env['DBUS_SESSION_BUS_ADDRESS']
 a11y=launch('a11y-dbus',['dbus-daemon','--session','--nofork','--print-address=1'],subprocess.PIPE)
 env['AT_SPI_BUS_ADDRESS']=a11y.stdout.readline().strip();assert env['AT_SPI_BUS_ADDRESS']
 registry=launch('a11y-registry',['/nix/store/iw5kcyxqr3c4w4m2d2yaqxkkis07awr3-at-spi2-core-2.60.6/libexec/at-spi2-registryd'])
 for attempt in range(30):
  check=subprocess.run(['busctl','--address='+env['AT_SPI_BUS_ADDRESS'],'call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','NameHasOwner','s','org.a11y.atspi.Registry'],env=env,capture_output=True,text=True,timeout=2)
  if 'true' in check.stdout:break
  time.sleep(.1)
 else:raise RuntimeError('Private accessibility registry did not acquire its name')
 env['WAYLAND_DISPLAY']=parent
 config=out/'hyprland.conf';config.write_text('monitor = ,1280x800@60,0x0,1\nanimations {\n enabled = false\n}\nmisc {\n disable_hyprland_logo = true\n disable_splash_rendering = true\n}\nxwayland {\n enabled = false\n}\nplugin = '+str(old)+'\n')
 compositor=launch('hyprland',['Hyprland','--config',str(config)])
 wait_for(lambda:bool(list(runtime.glob('hypr/*/.socket.sock'))),compositor)
 env['HYPRLAND_INSTANCE_SIGNATURE']=next(runtime.glob('hypr/*/.socket.sock')).parent.name
 wait_for(lambda:len([p for p in runtime.glob('wayland-*') if not p.name.endswith('.lock') and p.name!=parent])==1,compositor)
 env['WAYLAND_DISPLAY']=next(p for p in runtime.glob('wayland-*') if not p.name.endswith('.lock') and p.name!=parent).name
 ctl('output','create','headless','TEST')
 env.update(GDK_BACKEND='wayland',NO_AT_BRIDGE='0',GTK_MODULES='gail:atk-bridge')
 saved=json.loads((testing/'live-session/env.json').read_text());env['GI_TYPELIB_PATH']=saved['GI_TYPELIB_PATH']
 launch('seat',[str(testing/'runtime-result/bin/hypr-use-test-seat')])
 fixture=out/'fixture';fixture.mkdir();app=launch('fixture',[str(testing/'runtime-result/bin/python3'),str(testing/'unified-benchmark/fixture.py'),str(fixture),'0'])
 wait_for(lambda:any(w['class']=='hypr-use-bench' for w in clients()),app)
 target=next(w for w in clients() if w['class']=='hypr-use-bench');assert target['pid']==app.pid
 ctl('dispatch','movetoworkspacesilent','2,address:'+target['address'])
 sentinel=launch('sentinel',[str(testing/'runtime-result/bin/python3'),str(testing/'sentinel.py')])
 wait_for(lambda:any(w['pid']==sentinel.pid for w in clients()),sentinel)
 sentinel_window=next(w for w in clients() if w['pid']==sentinel.pid);ctl('dispatch','focuswindow','address:'+sentinel_window['address'])
 def monitor():
  while not monitor_stop.wait(.05):
   try:
    active=json.loads(ctl('-j','activewindow'));focus.append({'time':time.time(),'pid':active.get('pid'),'target_refocused':active.get('pid')==app.pid})
   except Exception:pass
 thread=threading.Thread(target=monitor,daemon=True);thread.start()
 env.update(HYPR_AGENT_PORTAL_PERMISSION_MODE='full',HYPR_AGENT_PORTAL_APPROVAL_POLICY='never',HYPR_AGENT_PORTAL_CONFINE='class:hypr-use-bench',HYPR_USE_WIRE_LOG=str(out/'wire.jsonl'),HYPR_USE_PORTAL_LOG=str(out/'portal.jsonl'))
 mcp=subprocess.Popen(['node',str(root/'mcp/unified/server.mjs')],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(out/'mcp.stderr').open('w'),text=True,start_new_session=True);processes.append(mcp)
 seq=0
 def js(code):
  global seq
  seq+=1;mcp.stdin.write(json.dumps({'jsonrpc':'2.0','id':seq,'method':'tools/call','params':{'name':'js','arguments':{'code':code}}})+'\n');mcp.stdin.flush();result=json.loads(mcp.stdout.readline());(out/f'response-{seq}.json').write_text(json.dumps(result));assert not result['result'].get('isError'),str(result)[:400]
 def state():return json.loads((out/'portal.jsonl').read_text().splitlines()[-1])['response']['result']['structuredContent']
 for label,plugin in [('old',old),('new',new)]:
  if label=='new':ctl('plugin','unload',str(old));ctl('plugin','load',str(new))
  js("var app=await cua.getApp('hypr-use-bench');")
  assert state()['window']['pid']==app.pid
  for attempt in range(12):
   if any(e.get('name')=='Country' and e.get('controlType')=='combo box' for e in state().get('elements',[])):break
   time.sleep(.25);js('await app.getAXState();')
  country=next(e for e in state()['elements'] if e['name']=='Country' and e['controlType']=='combo box');assert country['value']=='Japan'
  js(f"await app.click({country['index']});await app.getAXState();")
  germany=next(e for e in state()['elements'] if e['name']=='Germany' and e['controlType']=='menu item')
  if label=='new' and '--inspect' in sys.argv:
   frame=germany['frame'];payload=f"{state()['target']},{frame['x']+frame['width']/2},{frame['y']+frame['height']/2},inspect"
   inspection=subprocess.run(['hyprctl','dispatch','hypr-agent-portal:pointer-relative',payload],env=env,capture_output=True,text=True)
   (out/'surface-inspect.txt').write_text(inspection.stdout+inspection.stderr)
  js(f"await app.click({germany['index']});await app.getAXState();")
  actual=json.loads((fixture/'state.json').read_text());row={'route':label,'selected':actual.get('Country'),'passed':actual.get('Country')=='Germany','plugin':str(plugin),'sha256':hashlib.sha256(plugin.read_bytes()).hexdigest()};rows.append(row);print(json.dumps(row),flush=True)
finally:
 monitor_stop.set()
 for p in reversed(processes):
  if p.poll() is None:
   try:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=5)
   except ProcessLookupError:pass
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
 (out/'results.json').write_text(json.dumps({'cases':rows,'focus':focus,'refocus':any(f['target_refocused'] for f in focus),'error':str(sys.exc_info()[1]) if sys.exc_info()[1] else None},indent=2))
