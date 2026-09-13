import subprocess,json,os
from pathlib import Path
r=Path(__file__).resolve().parents[2]
e=os.environ.copy();e.update(HYPR_AGENT_PORTAL_PERMISSION_MODE='full',HYPR_AGENT_PORTAL_APPROVAL_POLICY='never')
p=subprocess.run(['node',str(r/'mcp/unified/server.mjs')],input=json.dumps({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'js','arguments':{'code':'await cua.listApps();','timeout_ms':20000}}})+'\n',capture_output=True,text=True,env=e,timeout=30)
print(p.stdout[:4500]);print(p.stderr[:1000])
