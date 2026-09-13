import os,sys,json,subprocess,importlib.util,time
from pathlib import Path
r=Path(__file__).resolve().parent;out=r/'a11y-experiments'
if not os.environ.get('HYPR_A11Y_EXPERIMENT'):
 e=json.loads((out/'session/env.json').read_text());e.update(HYPR_A11Y_EXPERIMENT='1',HYPR_AGENT_PORTAL_PERMISSION_MODE='full',HYPR_AGENT_PORTAL_APP_POLICIES='*=full',HYPR_AGENT_PORTAL_CLIPBOARD='none',GTK_MODULES='gail:atk-bridge',GTK_A11Y='always');e['PATH']=str(r/'runtime-result/bin')+':'+e['PATH'];os.execve(str(r/'runtime-result/bin/python3'),['python3',__file__],e)
subprocess.run(['busctl','--address='+os.environ['DBUS_SESSION_BUS_ADDRESS'],'set-property','org.a11y.Bus','/org/a11y/bus','org.a11y.Status','IsEnabled','b','true'],check=True)
f=subprocess.Popen([sys.executable,str(r/'a11y-experiment-fixture.py')],stdout=(out/'fixture.log').open('w'),stderr=subprocess.STDOUT)
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
m=load('portal',r.parent/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py');m.ensure_session_environment();load('timing',r/'portal-timing.py').install(m)
results=[]
try:
 for _ in range(60):
  ws=json.loads(subprocess.check_output(['hyprctl','-j','clients'],text=True))
  if any(w['pid']==f.pid for w in ws):break
  time.sleep(.1)
 w=next(w for w in ws if w['pid']==f.pid);app=m.window_selector(w)
 def call(name,args):
  response=m.handle({'jsonrpc':'2.0','id':len(results)+1,'method':'tools/call','params':{'name':name,'arguments':{'app':app,**args}}});results.append({'tool':name,'args':args,'response':response});(out/'wire.json').write_text(json.dumps(results));return response['result']
 time.sleep(1)
 s=call('get_app_state',{})['structuredContent'];button=next(e for e in s['elements'] if e.get('name')=='Record offscreen action');print('offscreen frame',button.get('frame'),flush=True)
 for attempt in range(3):
  if attempt==1:
   call('manage_window',{'action':'floating'})
   changed=call('manage_window',{'action':'resize','width':650,'height':420})
   assert not changed.get('isError'), changed.get('content')
  result=call('click',{'element_index':int(button['index']),'element_click_mode':'atspi'});state=json.loads((out/'fixture-state.json').read_text());print('attempt',attempt,'error',result.get('isError'),'state',state,flush=True)
  if result.get('isError'):print(str(result.get('content'))[:1000],flush=True);break
  assert state['clicks']==attempt+1
  button=next(e for e in result['structuredContent']['elements'] if e.get('name')=='Record offscreen action')
 # Exercise a popup selection whose geometry need not fit the parent capture.
 combo=next(e for e in result['structuredContent']['elements'] if e.get('controlType')=='combo box')
 opened=call('click',{'element_index':int(combo['index']),'element_click_mode':'atspi'})
 print('combo opened',not opened.get('isError'),flush=True)
 snap=opened.get('structuredContent',{})
 choices=[e for e in snap.get('elements',[]) if e.get('name')=='ODF Spreadsheet']
 print('choices',[(e['index'],e.get('frame'),e.get('actions')) for e in choices],flush=True)
 if choices:
  selected=call('click',{'element_index':int(choices[-1]['index']),'element_click_mode':'atspi'})
  print('selection error',selected.get('isError'),'state',json.loads((out/'fixture-state.json').read_text()),flush=True)
 (out/'results.json').write_text(json.dumps({'attempts':5,'observed_clicks':json.loads((out/'fixture-state.json').read_text())['clicks'],'isolated':True,'observed_format':json.loads((out/'fixture-state.json').read_text())['format'],'resized_between_snapshot_and_click':True},indent=2))
finally:
 f.terminate();f.wait(timeout=5)
