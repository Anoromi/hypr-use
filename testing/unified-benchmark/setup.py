import os,json,subprocess,shlex,time,sys
from pathlib import Path
from monitor import Monitor,ctl
r=Path(__file__).resolve().parents[2];out=r/'testing/unified-benchmark/live';out.mkdir(parents=True,exist_ok=True)
monitor=Monitor(out/'setup-focus.jsonl',['hypr-use-bench','libreoffice-calc','libreoffice-startcenter','soffice'])
e=os.environ.copy();saved=json.loads((r/'testing/live-session/env.json').read_text())
for k in ['GI_TYPELIB_PATH','XDG_DATA_DIRS']:
 if saved.get(k):e[k]=saved[k]
e.update(GDK_BACKEND='wayland',GTK_MODULES='gail:atk-bridge',NO_AT_BRIDGE='0',SAL_USE_VCLPLUGIN='gtk3',SAL_DISABLE_OPENCL='1')
# Named temporary rules only cover our fixture and otherwise absent LibreOffice.
assert not any('libreoffice' in w['class'] or w['class']=='soffice' for w in ctl('clients')),'LibreOffice already running'
rule='hl.window_rule({name="hypr-use-benchmark",match={class="^(hypr-use-bench|libreoffice.*|soffice)$"},no_initial_focus=true,suppress_event="activate activatefocus",workspace="902 silent"}):set_enabled(true)'
p=subprocess.run(['hyprctl','eval',rule],text=True,capture_output=True);assert p.returncode==0,p.stdout+p.stderr
commands=[[str(r/'testing/runtime-result/bin/python3'),str(Path(__file__).with_name('fixture.py')),str(out/'fixture'),sys.argv[2] if len(sys.argv)>2 else '0'],['libreoffice','-env:UserInstallation='+ (out/('calc-profile-'+sys.argv[1] if len(sys.argv)>1 else 'calc-profile')).as_uri(),'--norestore','--nofirststartwizard','--calc']]
for i,cmd in enumerate(commands):
 if monitor.trigger.is_set():break
 launch=['env',*[f'{k}={e[k]}' for k in ['GDK_BACKEND','GTK_MODULES','NO_AT_BRIDGE','GI_TYPELIB_PATH','XDG_DATA_DIRS','SAL_USE_VCLPLUGIN','SAL_DISABLE_OPENCL'] if k in e],*cmd]
 command='[workspace 902 silent] '+shlex.join(launch)+' > '+shlex.quote(str(out/f'app-{i}.log'))+' 2>&1'
 result=subprocess.run(['hyprctl','eval','hl.dispatch(hl.dsp.exec_cmd('+json.dumps(command)+'))'],text=True,capture_output=True)
 monitor.record('launch',{'command':cmd,'result':result.stdout});time.sleep(2)
for _ in range(25):
 ws=ctl('clients')
 if any(w['class']=='libreoffice-calc' for w in ws):break
 time.sleep(.2)
(out/'setup.json').write_text(json.dumps({'windows':ctl('clients'),'violations':monitor.violations},indent=2));monitor.close();print([(w['class'],w['title'],w['workspace']['id']) for w in ctl('clients')]);print('Refocuses:',monitor.violations)
