#!/usr/bin/env python3
"""Confined Calc test. All GUI actions still pass through Portal's policy."""
import importlib.util,json,os,sys,time
from pathlib import Path
r=Path(__file__).resolve().parent
if os.environ.get('HYPR_USE_CALC_RUNTIME') != '1':
    e=json.loads((r/'live-session/env.json').read_text())
    e.update(HYPR_USE_CALC_RUNTIME='1',HYPR_AGENT_PORTAL_APP_POLICIES='libreoffice*=full,soffice*=full',HYPR_AGENT_PORTAL_CONFINE='class:libreoffice*,class:soffice*',HYPR_AGENT_PORTAL_CLIPBOARD='none',HYPR_AGENT_PORTAL_PERMISSION_MODE='full')
    e['PATH']=str(r/'runtime-result/bin')+':'+e['PATH']
    os.execve(str(r/'runtime-result/bin/python3'),['python3',__file__],e)
p=r.parent/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py'
sys.path.insert(0,str(p.parent))
spec=importlib.util.spec_from_file_location('calc_portal',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original_parts=m.launch_parts
def calc_parts(args):
    if args != {'app':'libreoffice'}:
        raise RuntimeError('This recorded test authorizes only launch_app app=libreoffice')
    return original_parts(args)
m.launch_parts=calc_parts
launch=m.hyprctl_exec
def calc_launch(command):
    # Test setup pins launches to the user-requested background workspace.
    return launch('[workspace 2 silent] '+command)
m.hyprctl_exec=calc_launch
# Keep detailed durations in response metadata and the existing wire recording.
timing_spec=importlib.util.spec_from_file_location('portal_timing',r/'portal-timing.py')
timing_module=importlib.util.module_from_spec(timing_spec);timing_spec.loader.exec_module(timing_module)
timing_module.install(m)
original_handle=m.handle
def recorded_handle(request):
    started=time.time()
    result=original_handle(request)
    if request.get('method') == 'tools/call':
        with (r/'calc-session/wire.jsonl').open('a') as log:
            log.write(json.dumps({'time':started,'duration_ms':round((time.time()-started)*1000),'request':request,'response':result})+'\n')
    return result
m.handle=recorded_handle
raise SystemExit(m.main())
