"""Reproduce OSWorld closed-tab state in an owned background Chromium profile."""
import json,os,subprocess,time,urllib.request,socket,sys
from pathlib import Path
from monitor import Monitor,ctl
here=Path(__file__).resolve().parent;out=here/os.environ.get('HYPR_USE_RESTORE_PHASE','astra-published-restore');out.mkdir(exist_ok=True)
app='hypr-use-restore-bench';profile=out/'chrome-profile'
assert not profile.exists(),'Do not reuse previously prepared state'
assert not any(w['class']==app for w in ctl('clients')),'Close the owned browser from the previous setup first'
monitor=Monitor(out/'setup-focus.jsonl',[app]);browser=None
urls=['https://www.lonelyplanet.com','https://www.airbnb.com','https://www.tripadvisor.com']
rule='hl.window_rule({name="hypr-use-restore-benchmark",match={class="^hypr-use-restore-bench$"},no_initial_focus=true,suppress_event="activate activatefocus",workspace="902 silent"}):set_enabled(true)'
r=subprocess.run(['hyprctl','eval',rule],capture_output=True,text=True);assert r.stdout.strip()=='ok',r.stdout
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
cmd=['/etc/profiles/per-user/anoromi/bin/chromium','--user-data-dir='+str(profile),'--class='+app,'--ozone-platform=wayland','--force-renderer-accessibility','--no-first-run','--no-default-browser-check','--remote-debugging-address=127.0.0.1','--remote-debugging-port='+str(port),*urls]
log=(out/'browser.log').open('w');browser_env=os.environ.copy()
if os.environ.get('HYPR_USE_WAYLAND_TRACE'):browser_env['WAYLAND_DEBUG']='client'
browser=subprocess.Popen(cmd,stdout=log,stderr=log,start_new_session=True,env=browser_env)
monitor.callback=lambda:browser.terminate() if browser.poll() is None else None
(out/'owned-browser.json').write_text(json.dumps({'pid':browser.pid,'port':port,'profile':str(profile),'command':cmd},indent=2))
def tabs():return json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list',timeout=2))
try:
 for _ in range(100):
  assert not monitor.trigger.is_set(),'Setup refocus detected'
  try:
   pages=[x for x in tabs() if x['type']=='page'];target=next((x for x in pages if 'tripadvisor.com' in x['url']),None)
   if target and len(pages)==3:break
  except Exception:pass
  time.sleep(.2)
 else:raise RuntimeError('Three benchmark tabs not available')
 # A target URL in /json/list can be provisional: wait for a committed entry.
 for _ in range(90):
  assert not monitor.trigger.is_set(),'Setup refocus detected'
  nav=json.loads(subprocess.check_output(['node',str(here/'chromium-navigation.mjs'),str(port)],text=True,timeout=10))
  committed=[]
  for t in nav:
   h=t['history'].get('result',{});entries=h.get('entries',[]);idx=h.get('currentIndex',-1)
   committed.append(0<=idx<len(entries) and entries[idx].get('url','').rstrip('/')==t['url'].rstrip('/') and bool(t['title']))
  if len(nav)==3 and all(committed):break
  time.sleep(.5)
 else:raise RuntimeError('Refusing benchmark: tabs have no confirmed committed navigation')
 (out/'navigation-before-close.json').write_text(json.dumps(nav,indent=2))
 pages=[x for x in tabs() if x['type']=='page'];target=next(x for x in pages if 'tripadvisor.com' in x['url'])
 (out/'tabs-before-close.json').write_text(json.dumps(pages,indent=2))
 urllib.request.urlopen(f'http://127.0.0.1:{port}/json/close/'+target['id']).read()
 time.sleep(1)
 pages=[x for x in tabs() if x['type']=='page'];assert len(pages)==2 and all('tripadvisor.com' not in x['url'] for x in pages),pages
 (out/'tabs-start.json').write_text(json.dumps(pages,indent=2))
 windows=[x for x in ctl('clients') if x['class']==app];assert len(windows)==1,windows
 # Restore preflights are diagnostic only, never part of a clean benchmark.
 if os.environ.get('HYPR_USE_RESTORE_PREFLIGHT')=='1':
  # Validate restoration itself, then recreate the closed-tab state before timing.
  pre_env=os.environ.copy();pre_env.update(HYPR_USE_RESTORE_PHASE=out.name,HYPR_USE_PROBE_CASE='preflight',HYPR_USE_PROBE_CODES=json.dumps(["var app=await cua.getApp('hypr-use-restore-bench');", "await app.pressKey('Ctrl+Shift+t');"]))
  subprocess.run([sys.executable,str(here/'restore-input-probe.py')],env=pre_env,check=True,timeout=60)
  pages=[x for x in tabs() if x['type']=='page'];assert len(pages)==3 and any('tripadvisor.com' in x['url'] for x in pages),'Preflight cannot restore the intended tab'
  target=next(x for x in pages if 'tripadvisor.com' in x['url'])
  urllib.request.urlopen(f'http://127.0.0.1:{port}/json/close/'+target['id']).read();time.sleep(.3)
  pages=[x for x in tabs() if x['type']=='page'];assert len(pages)==2 and all('tripadvisor.com' not in x['url'] for x in pages)
  (out/'tabs-start.json').write_text(json.dumps(pages,indent=2))
 (out/'setup.json').write_text(json.dumps({'windows':windows,'active':ctl('activewindow'),'refocus':monitor.violations,'urls_before':urls,'closed_url':'https://www.tripadvisor.com','restore_preflight':os.environ.get('HYPR_USE_RESTORE_PREFLIGHT')=='1','close_count':2 if os.environ.get('HYPR_USE_RESTORE_PREFLIGHT')=='1' else 1},indent=2))
 print(json.dumps({'ready':True,'app':app,'tabs':[x['url'] for x in pages],'workspace':windows[0]['workspace']['id'],'refocus':monitor.violations}))
finally:monitor.close()
