"""Direct adapter validation, separate from model benchmarks."""
import os,sys,json,subprocess,signal,time
from pathlib import Path
from monitor import Monitor
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent
name=sys.argv[1];code=Path(sys.argv[2]).read_text();scope=sys.argv[3];out=here/'validation'/name;out.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env.update(HYPR_AGENT_PORTAL_PERMISSION_MODE='full',HYPR_AGENT_PORTAL_APPROVAL_POLICY='never',HYPR_AGENT_PORTAL_CONFINE=scope,HYPR_USE_WIRE_LOG=str(out/'wire.jsonl'),HYPR_USE_PORTAL_LOG=str(out/'portal.jsonl'))
monitor=Monitor(out/'focus.jsonl',['hypr-use-bench','libreoffice-calc','soffice','zen-beta']);child=None
monitor.callback=lambda: child.send_signal(signal.SIGTERM) if child and child.poll() is None else None
try:
 start=time.monotonic();child=subprocess.Popen(['node',str(root/'mcp/unified/server.mjs')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
 req={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'js','arguments':{'code':code,'timeout_ms':90000}}}
 stdout,stderr=child.communicate(json.dumps(req)+'\n',timeout=100);(out/'response.json').write_text(stdout);(out/'stderr.txt').write_text(stderr)
 result=json.loads(stdout).get('result',{});print(json.dumps({'seconds':time.monotonic()-start,'error':result.get('isError'),'refocus':monitor.violations,'operations':[(x['name'],round(x['duration_ms'],1)) for x in result.get('_meta',{}).get('hypr-use/timing',{}).get('operations',[])]}))
 for b in result.get('content',[]):
  if b.get('type')=='text' and (result.get('isError') or b.get('text','').startswith('VALIDATION')):print(b['text'][-1600:])
finally:
 monitor.close()
 if child and child.poll() is None:child.terminate();child.wait(timeout=5)
