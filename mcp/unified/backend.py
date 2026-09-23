"""Private portal transport; every desktop request passes through portal policy."""
import importlib.util,json,os,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'mcp'))
from server import load_backend
b=load_backend();b.ensure_session_environment()
from runtime_fixes import install as install_runtime_fixes
install_runtime_fixes(b)
if os.environ.get('HYPR_USE_FAST_CONTROL','1') != '0':
 from control import install
 control=install(b)
from image_transport import optimize_images
from observations import Observations
observations=Observations(b)
from session_events import SessionEvents
try:
 session_events=SessionEvents(b)
except OSError:
 session_events=None  # Original guarded polling remains active.
spec=importlib.util.spec_from_file_location('timing',root/'testing/portal-timing.py');timing=importlib.util.module_from_spec(spec);spec.loader.exec_module(timing);timing.install(b)
# Guard key/text/value actions too: they may map dialogs without pointer input.
for name in ('press_key','type_text','set_value','perform_secondary_action','paste_text'):
 original=b.SEMANTIC_TOOLS[name]
 def guarded(args,fn=original):
  snap=b.current_snapshot(args['app']);target=str(snap['target']);session=b.begin_related_action_session(target)
  if not session.get('begin',{}).get('ok'):raise RuntimeError('Background workspace guard unavailable')
  try:return fn(args)
  finally:b.finish_related_action_session(target,session)
 b.SEMANTIC_TOOLS[name]=guarded
for line in sys.stdin:
 try:
  req=json.loads(line)
  # This private observation selector does not change owner authorization.
  params=req.get('params',{});name=params.get('name')
  b.SNAPSHOT_INCLUDE_IMAGES=name in {'get_app_state','get_screenshot'}
  b.SNAPSHOT_INCLUDE_AX=name!='get_screenshot'
  if name in {'get_ax_state','get_screenshot'}:params['name']='get_app_state'
  start=time.monotonic();res=b.handle(req)
  if res and isinstance(res.get("result"),dict):optimize_images(res["result"])
  if name in {'get_ax_state','get_screenshot'}:params['name']=name
  if name in {'get_ax_state','get_app_state'} and res and not res.get('result',{}).get('isError'):
   observations.publish(params.get('arguments',{}).get('app'),res.get('result',{}).get('structuredContent'))
  record=os.environ.get('HYPR_USE_PORTAL_LOG')
  if record:
   with open(record,'a') as f:f.write(json.dumps({'time':time.time(),'duration_ms':(time.monotonic()-start)*1000,'request':req,'response':res})+'\n')
  if res is not None:print(json.dumps(res),flush=True)
 except Exception as e:print(json.dumps({'jsonrpc':'2.0','id':req.get('id'),'error':{'code':-32603,'message':str(e)}}),flush=True)
