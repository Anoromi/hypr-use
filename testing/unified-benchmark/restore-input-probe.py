import json,os,subprocess,time,urllib.request
from pathlib import Path
from monitor import Monitor
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent;out=here/os.environ.get('HYPR_USE_RESTORE_PHASE','restore-diagnosis');case=os.environ.get('HYPR_USE_PROBE_CASE','baseline');d=out/case;d.mkdir(exist_ok=False)
e=os.environ.copy();e.update(HYPR_AGENT_PORTAL_PERMISSION_MODE='full',HYPR_AGENT_PORTAL_APPROVAL_POLICY='never',HYPR_AGENT_PORTAL_CONFINE='class:hypr-use-restore-bench',HYPR_USE_WIRE_LOG=str(d/'wire.jsonl'),HYPR_USE_PORTAL_LOG=str(d/'portal.jsonl'))
owned=json.loads((out/'owned-browser.json').read_text());m=Monitor(d/'focus.jsonl',['hypr-use-restore-bench']);p=subprocess.Popen(['node',str(root/'mcp/unified/server.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(d/'stderr.txt').open('w'),text=True,env=e);m.callback=p.terminate
codes=["var app=await cua.getApp('hypr-use-restore-bench');", "await app.pressKey('Ctrl+Shift+t');", "await app.pressKey('Ctrl+t');"]
codes=json.loads(os.environ['HYPR_USE_PROBE_CODES']) if os.environ.get('HYPR_USE_PROBE_CODES') else codes
rows=[]
try:
 for i,code in enumerate(codes):
  p.stdin.write(json.dumps({'jsonrpc':'2.0','id':i+1,'method':'tools/call','params':{'name':'js','arguments':{'code':code,'timeout_ms':30000}}})+'\n');p.stdin.flush();r=json.loads(p.stdout.readline());(d/f'{i}.json').write_text(json.dumps(r));assert not r['result'].get('isError'),r
  time.sleep(.7);tabs=[x['url'] for x in json.load(urllib.request.urlopen(f"http://127.0.0.1:{owned['port']}/json/list")) if x['type']=='page'];rows.append({'code':code,'tabs':tabs});print(rows[-1],flush=True)
finally:
 p.stdin.close();p.wait(timeout=10);m.close();(d/'result.json').write_text(json.dumps({'steps':rows,'refocus':m.violations},indent=2))
