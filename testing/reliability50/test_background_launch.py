import json,os,shlex,signal,subprocess,sys,time
from pathlib import Path
here=Path(__file__).resolve().parent;root=here.parents[1];sys.path.insert(0,str(here.parent/'unified-benchmark'))
from monitor import Monitor,ctl
out=here/'launch-validation';out.mkdir(exist_ok=False)
saved=json.loads((root/'testing/live-session/env.json').read_text());m=Monitor(out/'focus.jsonl',['hypr-use-bench']);owned=None
rule='hl.window_rule({name="hypr-use-r50",match={class="^hypr-use-bench$"},no_initial_focus=true,suppress_event="activate activatefocus",workspace="902 silent"}):set_enabled(true)'
try:
 for i in range(10):
  assert not m.trigger.is_set();d=out/str(i);d.mkdir();subprocess.run(['hyprctl','eval',rule],check=True,capture_output=True)
  env={k:saved[k] for k in ['GI_TYPELIB_PATH','XDG_DATA_DIRS'] if k in saved};env.update(GDK_BACKEND='wayland',NO_AT_BRIDGE='0',GTK_MODULES='gail:atk-bridge')
  (d/'launch.json').write_text(json.dumps({'command':[str(root/'testing/runtime-result/bin/python3'),str(here.parent/'unified-benchmark/fixture.py'),str(d/'fixture'),'0'],'env':env}))
  command='[workspace 902 silent] '+shlex.join([sys.executable,str(here/'launch_owned.py'),str(d/'launch.json')])+' > '+shlex.quote(str(d/'app.log'))+' 2>&1'
  subprocess.run(['hyprctl','eval','hl.dispatch(hl.dsp.exec_cmd('+json.dumps(command)+'))'],check=True,capture_output=True)
  for _ in range(100):
   if (d/'owned-process.json').exists():owned=json.loads((d/'owned-process.json').read_text())
   windows=[w for w in ctl('clients') if w['class']=='hypr-use-bench']
   if windows:break
   time.sleep(.03)
  assert windows and all(w['workspace']['id']==902 for w in windows);time.sleep(.2);assert not m.trigger.is_set()
  os.killpg(owned['pid'],signal.SIGTERM);owned=None
  for _ in range(100):
   if not any(w['class']=='hypr-use-bench' for w in ctl('clients')):break
   time.sleep(.03)
  print('launch',i+1,'workspace 902, no refocus',flush=True)
finally:
 if owned:
  try:os.killpg(owned['pid'],signal.SIGTERM)
  except ProcessLookupError:pass
 subprocess.run(['hyprctl','eval','hl.window_rule({name="hypr-use-r50",match={class="^hypr-use-bench$"}}):set_enabled(false)'],capture_output=True)
 m.close();(out/'result.json').write_text(json.dumps({'refocus':m.violations,'completed_launches':i+1,'active_after':ctl('activewindow')['class']},indent=2))
