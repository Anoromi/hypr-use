"""Fresh owned browsers distinguish geometry from input-order failures. No agent scoring."""
import json,os,shlex,signal,socket,subprocess,sys,time,urllib.request
from pathlib import Path
here=Path(__file__).resolve().parent;root=here.parents[1];sys.path.insert(0,str(here.parent/'unified-benchmark'))
from monitor import Monitor,ctl
from web_fixture import Fixture
out=here/'diagnostics'/sys.argv[1];out.mkdir(parents=True,exist_ok=False)
cases=sys.argv[2:] or ['index-batch','point-batch','index-split','index-wait','shortcut-batch','shortcut-split']
app='hypr-use-r50-browser';assert not any(w['class']==app for w in ctl('clients'))
m=Monitor(out/'focus.jsonl',[app]);owned=None;p=None;fixture=None;results=[]
def stop():
 if owned:
  try:
   fields=Path(f"/proc/{owned['pid']}/stat").read_text().split(') ',1)[1].split()
   if fields[19]==owned['start']:os.killpg(owned['pid'],signal.SIGTERM)
  except (FileNotFoundError,ProcessLookupError):pass
 if p and p.poll() is None:
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
m.callback=stop
try:
 for case in cases:
  assert not m.trigger.is_set();m.stage=case;d=out/case;d.mkdir();fixture=Fixture()
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  start=f'http://127.0.0.1:{fixture.port}/start';destination=f'http://127.0.0.1:{fixture.port}/second'
  if case.startswith(('date','select','form','workflow-replace')):start=f'http://127.0.0.1:{fixture.port}/web'
  rule='hl.window_rule({name="hypr-use-r50-probe",match={class="^hypr-use-r50-browser$"},no_initial_focus=true,suppress_event="activate activatefocus",workspace="902 silent"}):set_enabled(true)'
  subprocess.run(['hyprctl','eval',rule],check=True,capture_output=True)
  cmd=['chromium','--user-data-dir='+str(d/'profile'),'--class='+app,'--ozone-platform=wayland','--force-renderer-accessibility','--no-first-run','--no-default-browser-check','--remote-debugging-address=127.0.0.1','--remote-debugging-port='+str(port),start]
  (d/'launch.json').write_text(json.dumps({'command':cmd,'env':{'NO_AT_BRIDGE':'0'}}))
  command='[workspace 902 silent] '+shlex.join([sys.executable,str(here/'launch_owned.py'),str(d/'launch.json')])+' > '+shlex.quote(str(d/'app.log'))+' 2>&1'
  subprocess.run(['hyprctl','eval','hl.dispatch(hl.dsp.exec_cmd('+json.dumps(command)+'))'],check=True,capture_output=True)
  for _ in range(200):
   if (d/'owned-process.json').exists():owned=json.loads((d/'owned-process.json').read_text())
   windows=[w for w in ctl('clients') if w['class']==app]
   if windows:break
   time.sleep(.03)
  assert windows and all(w['workspace']['id']==902 for w in windows)
  env={k:v for k,v in os.environ.items() if not k.startswith(('HYPR_USE_','HYPR_AGENT_PORTAL_'))}
  env.update(HYPR_AGENT_PORTAL_PERMISSION_MODE='full',HYPR_AGENT_PORTAL_APPROVAL_POLICY='never',HYPR_AGENT_PORTAL_CONFINE='class:'+app,HYPR_USE_WIRE_LOG=str(d/'wire.jsonl'),HYPR_USE_PORTAL_LOG=str(d/'portal.jsonl'))
  if 'debug' in case:env['HYPR_USE_AX_DEBUG_STACK']='1'
  p=subprocess.Popen(['node',str(root/'mcp/unified/server.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(d/'stderr.txt').open('w'),text=True,env=env,start_new_session=True)
  steps=[]
  def js(code,allow_error=False,tool=None):
   assert not m.trigger.is_set();begin=time.monotonic()
   p.stdin.write(json.dumps({'jsonrpc':'2.0','id':len(steps)+1,'method':'tools/call','params':{'name':tool or 'js','arguments':code if tool else {'code':code,'timeout_ms':30000}}})+'\n');p.stdin.flush()
   r=json.loads(p.stdout.readline());steps.append({'code':code,'seconds':time.monotonic()-begin,'error':r['result'].get('isError')})
   (d/f'response-{len(steps)}.json').write_text(json.dumps(r));assert allow_error or not r['result'].get('isError'),str(r)[:300]
   return r
  js("var app=await cua.getApp('"+app+"');")
  observation=json.loads((d/'portal.jsonl').read_text().splitlines()[-1])['response']['result']['structuredContent']
  entry=next(e for e in observation['elements'] if e['name']=='Address and search bar');frame=entry['frame'];point=[frame['x']+frame['width']/2,frame['y']+frame['height']/2]
  if 'capture' in case:js('await app.getScreenshot({emit:false});')
  if 'age' in case:time.sleep(3)
  click=f"await app.click({entry['index']});"
  if case.startswith('point'):click=f'await app.click({json.dumps(point)});'
  if case.startswith('left'):click=f"await app.click([{frame['x']+150}, {point[1]}]);"
  if case.startswith('shortcut'):click="await app.pressKey('Ctrl+l');"
  keys=["await app.pressKey('Ctrl+a');",'await app.typeText('+json.dumps(destination)+');',"await app.pressKey('Return');"]
  if case.startswith('form-cascade'):
   page=next(x for x in json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list',timeout=3)) if x['type']=='page')
   # Controller-only fixture setup: make a later field invalidate an earlier one.
   expression="document.getElementById('email').addEventListener('input',()=>{document.getElementById('name').value='Reset by email change';}); true"
   setup=json.loads(subprocess.check_output(['node',str(here/'cdp.mjs'),page['webSocketDebuggerUrl'],'Runtime.evaluate',json.dumps({'expression':expression,'returnByValue':True})],text=True))
   assert setup['result']['result']['value'] is True
   cascade=js('await app.fillForm('+json.dumps({'fields':[{'name':'Full name','value':'Grace Hopper','method':'keys'},{'name':'Email','value':'grace@example.test','method':'keys'}],'submit':{'name':'Save profile'}})+');',allow_error=True)
  elif case.startswith('form-checkbox'):
   fields=[{'name':'Email updates','value':True},{'name':'SMS updates','value':False}]
   js('await app.fillForm('+json.dumps({'fields':fields,'submit':{'name':'Save profile'}})+');')
   js('await app.fillForm('+json.dumps({'fields':fields})+'); await app.waitFor({target:{name:"Email updates"},value:true});')
  elif case.startswith('form-options'):
   choices=[{'name':'Category','option':'Accessories'},{'name':'Sort by price','option':'Lowest first'}]
   js({'app':app,'choices':choices},tool='select_options')
   js('await app.selectOptions('+json.dumps({'choices':choices})+');')
  elif case.startswith('form-direct'):
   js({'app':app,'fields':[{'name':'Full name','value':'Grace Hopper'},{'name':'Email','value':'grace@example.test'}],'submit':{'name':'Save profile'}},tool='fill_form')
  elif case.startswith('form-repeat'):
   fields=[{'name':'Full name','value':'Grace Hopper'},{'name':'Email','value':'grace@example.test'}]
   js('await app.fillForm('+json.dumps({'fields':fields,'submit':{'name':'Save profile'}})+');')
   js('await app.fillForm('+json.dumps({'fields':fields})+');')
  elif case.startswith('form'):
   method='keys' if 'keys' in case else None
   js('await app.fillForm('+json.dumps({'fields':[{'name':'Full name','value':'Grace Hopper',**({'method':method} if method else {})},{'name':'Email','value':'grace@example.test',**({'method':method} if method else {})}],'submit':{'name':'Save profile'}})+');')
  elif case.startswith('workflow-replace'):
   js("await app.replaceText({target:{name:'Note'},text:'alpha DELTA gamma'});")
   if case.endswith('clear'):
    state=json.loads((d/'portal.jsonl').read_text().splitlines()[-1])['response']['result']['structuredContent']
    assert any(e.get('name')=='Note' and e.get('value')=='alpha DELTA gamma' for e in state['elements'])
    js("await app.replaceText({target:{name:'Note'},text:''});")
   save=next(e for e in observation['elements'] if e['name']=='Save profile');js(f"await app.click({save['index']}); await app.getAXState();")
  elif case.startswith('workflow-nav'):
   js('await app.navigate('+json.dumps({'url':destination})+'); await app.waitFor({text:"heading Second"});')
  elif case.startswith('select'):
   note=next(e for e in observation['elements'] if e['name']=='Note');save=next(e for e in observation['elements'] if e['name']=='Save profile')
   js(f"await app.click({note['index']}); await app.typeText('alpha beta gamma'); await app.getAXState();")
   selection=js(f"await app.selectText({note['index']}, 'beta');",allow_error=True)
   if not selection['result'].get('isError'):js(f"await app.typeText('DELTA'); await app.click({save['index']}); await app.getAXState();")
  elif case.startswith('date'):
   elements=observation['elements'];parts=[next(e for e in elements if e['name']==name)['index'] for name in ['Month Appointment','Day Appointment','Year Appointment']]
   save=next(e for e in elements if e['name']=='Save profile')['index'];code=''
   for index,value in zip(parts,['10','21','2026']):code+=f'await app.click({index});'+(f"await app.pressKey('{ ' '.join(value) }');" if 'sequence' in case else f"await app.typeText('{value}');")
   js(code+f"await app.pressKey('Tab'); await app.click({save}); await app.getAXState();")
  elif case.endswith('observe'):js(click+'await app.getAXState();');js(''.join(keys)+'await app.getAXState();')
  elif case.endswith('observe-image'):js(click+'await app.getAXStateAndScreenshot();');js(''.join(keys)+'await app.getAXState();')
  elif case.endswith('split'):
   for code in [click,*keys]:js(code);time.sleep(.25)
   js('await app.getAXState();')
  elif case.endswith('wait'):js(click);time.sleep(.4);js(''.join(keys)+'await app.getAXState();')
  else:js(click+''.join(keys)+'await app.getAXState();')
  time.sleep(.4)
  urls=[v['url'] for v in json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list',timeout=3)) if v['type']=='page']
  passed=fixture.state.get('date')=='2026-10-21' and fixture.state.get('saved') is True if case.startswith('date') else destination in urls
  if case.startswith('select'):passed=fixture.state.get('note')=='alpha DELTA gamma' and fixture.state.get('saved') is True
  if case.startswith('form'):passed=fixture.state.get('name')=='Grace Hopper' and fixture.state.get('email')=='grace@example.test' and fixture.state.get('saved') is True
  if case.startswith('workflow-replace'):passed=fixture.state.get('note')==('' if case.endswith('clear') else 'alpha DELTA gamma') and fixture.state.get('saved') is True
  if case.startswith('form-checkbox'):passed=fixture.state.get('updates') is True and fixture.state.get('sms') is False and fixture.state.get('saved') is True
  if case.startswith('form-options'):passed=fixture.state.get('category')=='Accessories' and fixture.state.get('sort')=='ascending'
  if case.startswith('form-cascade'):passed=cascade['result'].get('isError') is True and 'changed after a later input' in json.dumps(cascade) and fixture.state.get('saved') is not True
  row={'case':case,'passed':passed,'urls':urls,'steps':steps,'refocus':m.trigger.is_set()}
  if case.startswith(('date','select','form','workflow-replace')):row['state']=fixture.state
  results.append(row);print(json.dumps(row),flush=True)
  p.stdin.close();p.wait(timeout=10);p=None;stop();owned=None;fixture.close();fixture=None
  for _ in range(100):
   if not any(w['class']==app for w in ctl('clients')):break
   time.sleep(.03)
finally:
 stop()
 if fixture:fixture.close()
 subprocess.run(['hyprctl','eval','hl.window_rule({name="hypr-use-r50-probe",match={class="^hypr-use-r50-browser$"}}):set_enabled(false)'],capture_output=True)
 m.close();(out/'results.json').write_text(json.dumps({'cases':results,'refocus':m.violations,'completed_all':len(results)==len(cases),'error':str(sys.exc_info()[1])[:500] if sys.exc_info()[1] else None},indent=2))
