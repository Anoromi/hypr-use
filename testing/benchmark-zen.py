import importlib.util,json,os,sys,subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parent
if os.environ.get('HYPR_USE_ZEN_TIMING')!='1':
 e=json.loads((r/'live-session/env.json').read_text());e['PATH']=str(r/'runtime-result/bin')+':'+e['PATH']
 e.update(HYPR_USE_ZEN_TIMING='1',HYPR_AGENT_PORTAL_PERMISSION_MODE='full',HYPR_AGENT_PORTAL_APP_POLICIES='zen-beta=full',HYPR_AGENT_PORTAL_CONFINE='class:zen-beta',HYPR_AGENT_PORTAL_CLIPBOARD='none')
 os.execve(str(r/'runtime-result/bin/python3'),['python3',__file__,*sys.argv[1:]],e)
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
m=load('zen_portal',r.parent/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py');load('timing',r/'portal-timing.py').install(m)
m.ensure_session_environment()
clients=json.loads(subprocess.check_output(['hyprctl','-j','clients'],text=True));zen=[c for c in clients if c['class']=='zen-beta'];assert len(zen)==1,'Expected one Zen window'
w=zen[0];target=m.window_selector(w)
out=r/'zen-timing';out.mkdir(exist_ok=True)
focus=lambda:json.loads(subprocess.check_output(['hyprctl','-j','activewindow'],text=True))
initial=focus();records=[]
try:
 for name,args in [('get_app_state',{}),('press_key',{'key':'ctrl+l' if '--address-bar' in sys.argv else 'ctrl+t'}),('type_text',{'method':'keys','text':'https://www.google.com'}),('press_key',{'key':'Return'}),('get_app_state',{})]:
  req={'jsonrpc':'2.0','id':len(records)+1,'method':'tools/call','params':{'name':name,'arguments':{'app':target,**args}}}
  start=time.time();res=m.handle(req);records.append({'time':start,'request':req,'response':res})
  (out/'wire.json').write_text(json.dumps(records))
  result=res.get('result',{});timing=result.get('_meta',{}).get('hypr-use/timing',{})
  print(name,round(timing.get('total_ms',0),1),'ms','error',result.get('isError'),flush=True)
  if result.get('isError'):
   print(str(result.get('content'))[:1400],flush=True);break
  if name=='press_key' and args.get('key')=='Return':time.sleep(2)
finally:
 (out/'focus.json').write_text(json.dumps({'before':initial,'after':focus()}))
