import os,sys,json,subprocess,importlib.util,time
from pathlib import Path
r=Path(__file__).resolve().parent;out=r/'a11y-experiments'
if not os.environ.get('HYPR_CALC_EXPERIMENT'):
 e=json.loads((out/'session/env.json').read_text());e.update(HYPR_CALC_EXPERIMENT='1',HYPR_AGENT_PORTAL_PERMISSION_MODE='full',HYPR_AGENT_PORTAL_APP_POLICIES='*=full',HYPR_AGENT_PORTAL_CLIPBOARD='none',GTK_MODULES='gail:atk-bridge',SAL_USE_VCLPLUGIN='gtk3',GDK_BACKEND='wayland');e['PATH']=str(r/'runtime-result/bin')+':'+e['PATH'];os.execve(str(r/'runtime-result/bin/python3'),['python3',__file__,*sys.argv[1:]],e)
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
m=load('isolated_calc',r.parent/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py');m.ensure_session_environment()
if sys.argv[1]=='launch':
 p=subprocess.Popen(['libreoffice','-env:UserInstallation='+(out/'calc-profile').as_uri(),'--norestore','--calc'],stdout=(out/'calc.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True);(out/'calc-pid').write_text(str(p.pid));print('launched',p.pid);sys.exit()
ws=json.loads(subprocess.check_output(['hyprctl','-j','clients'],text=True));ws=[w for w in ws if w.get('class','').startswith(('libreoffice','soffice'))];print('windows',[(w['address'],w['title']) for w in ws])
a=json.loads(sys.argv[2]) if len(sys.argv)>2 else {};target=a.pop('target',None)
w=next((w for w in ws if w['address']==target or w['title']==target),ws[-1]);app=m.window_selector(w)
def call(name,args):
 req={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':{'app':app,**args}}};res=m.handle(req)
 with (out/'calc-wire.jsonl').open('a') as f:f.write(json.dumps({'request':req,'response':res})+'\n')
 (out/'calc-last.json').write_text(json.dumps(res))
 return res['result']
s=call('get_app_state',{})
if sys.argv[1]!='state':
 if 'name' in a:
  name=a.pop('name');matches=[e for e in s['structuredContent']['elements'] if e.get('name')==name];print('matches',[(e['index'],e.get('controlType'),e.get('actions'),e.get('frame')) for e in matches]);a['element_index']=int(matches[-1]['index'])
 s=call(sys.argv[1],a)
print('error',s.get('isError'));st=s.get('structuredContent',{});print('title',st.get('windowTitle'));print('related',[(w.get('address'),w.get('title')) for w in st.get('relatedWindows',[])])
if s.get('isError'):print(s.get('content'))
else:print('elements',[(e['index'],e.get('name'),e.get('controlType'),e.get('value')) for e in st.get('elements',[]) if e.get('actions') or e.get('editable')][:150])
