#!/usr/bin/env python3
import json, os, subprocess, time, tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
run=root/'session'; run.mkdir(mode=0o700,exist_ok=True)
runtime=Path(tempfile.mkdtemp(prefix='hypr-use-'))
env={k:os.environ[k] for k in ('PATH','XDG_DATA_DIRS','LD_LIBRARY_PATH') if k in os.environ}
for k in ('DISPLAY','WAYLAND_DISPLAY','HYPRLAND_INSTANCE_SIGNATURE','DBUS_SESSION_BUS_ADDRESS'): env.pop(k,None)
env.update(XDG_RUNTIME_DIR=str(runtime),XDG_CONFIG_HOME=str(run),XDG_STATE_HOME=str(run/'state'),XDG_CACHE_HOME=str(run/'cache'),HYPRLAND_NO_SD_VARS='1',LIBSEAT_BACKEND='hypr-use-disabled',AQ_DRM_DEVICES='/nonexistent-hypr-use-device')
if (run/'pids.json').exists():
    for pid in json.loads((run/'pids.json').read_text()).values():
        if Path(f'/proc/{pid}/cmdline').exists() and str(root).encode() in Path(f'/proc/{pid}/cmdline').read_bytes():
            raise SystemExit('Test is already running. Run stop-test.py first.')
processes={}
def launch(name,args,e=env):
    p=subprocess.Popen(args,env=e,stdout=(run/(name+'.log')).open('w'),stderr=subprocess.STDOUT,start_new_session=True)
    processes[name]=p.pid
    (run/'pids.json').write_text(json.dumps(processes,indent=2))
    return p
def wait(check,p):
    for _ in range(100):
        if check():return
        if p.poll() is not None:raise RuntimeError(f'Process {p.pid} exited; inspect logs')
        time.sleep(.1)
    raise RuntimeError('Startup timeout')
env.update(WLR_BACKENDS='headless',WLR_RENDERER='gles2',WLR_HEADLESS_OUTPUTS='1')
weston=launch('cage',[str(root/'runtime-result/bin/cage'),'-s','--','sleep','3600'])
wait(lambda:bool(list(runtime.glob('wayland-*.lock'))),weston)
parent=next(runtime.glob('wayland-*.lock')).name.removesuffix('.lock')
bus=subprocess.Popen(['dbus-daemon','--session','--nofork','--print-address=1'],env=env,stdout=subprocess.PIPE,stderr=(run/'dbus.log').open('w'),text=True,start_new_session=True)
processes['dbus']=bus.pid;env['DBUS_SESSION_BUS_ADDRESS']=bus.stdout.readline().strip()
env['WAYLAND_DISPLAY']=parent
config=run/'hyprland.conf'
config.write_text('monitor = ,1280x800@60,0x0,1\nanimations {\n enabled = false\n}\nmisc {\n disable_hyprland_logo = true\n disable_splash_rendering = true\n}\nxwayland {\n enabled = false\n}\nplugin = '+str((root/'plugin-result/lib/libhypr-agent-portal.so').resolve())+'\n')
old_instances={x.name for x in (runtime/'hypr').glob('*')}
p=launch('hyprland',['Hyprland','--config',str(config)])
wait(lambda:bool([x for x in (runtime/'hypr').glob('*/.socket.sock') if x.parent.name not in old_instances]),p)
instance=next(x for x in (runtime/'hypr').glob('*/.socket.sock') if x.parent.name not in old_instances).parent.name
env['HYPRLAND_INSTANCE_SIGNATURE']=instance
sockets=[x for x in runtime.glob('wayland-*') if not x.name.endswith('.lock') and x.name != parent]
assert len(sockets)==1,sockets
env['WAYLAND_DISPLAY']=sockets[0].name
subprocess.run(['hyprctl','output','create','headless','TEST'],env=env,check=True,capture_output=True)
env['GDK_BACKEND']='wayland'
env['NO_AT_BRIDGE']='0'
launch('keyboard',[str(root/'runtime-result/bin/hypr-use-test-seat')])
deps=subprocess.check_output(['nix-store','-qR',str((root/'runtime-result').resolve())],text=True).splitlines()
env['GI_TYPELIB_PATH']=':'.join(str(Path(d)/'lib/girepository-1.0') for d in deps if (Path(d)/'lib/girepository-1.0').is_dir())
(run/'env.json').write_text(json.dumps(env,indent=2));os.chmod(run/'env.json',0o600)
launch('fixture',[str(root/'runtime-result/bin/python3'),str(root/'fixture.py')])
time.sleep(1)
launch('sentinel',[str(root/'runtime-result/bin/python3'),str(root/'sentinel.py')])
print(json.dumps({'session':str(run),'instance':instance,'pids':processes},indent=2))
