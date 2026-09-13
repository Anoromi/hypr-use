import json,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parent
p=subprocess.Popen(['python3',str(r/'mcp-live-server.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(r/'live-session/probe.stderr').open('w'),text=True)
def rpc(n,method,params):
 p.stdin.write(json.dumps({'jsonrpc':'2.0','id':n,'method':method,'params':params})+'\n');p.stdin.flush()
 while True:
  line=p.stdout.readline()
  if not line:raise RuntimeError('MCP closed')
  x=json.loads(line)
  if x.get('id')==n:return x
try:
 rpc(1,'initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'hypr-use-debug','version':'1'}})
 p.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/initialized'})+'\n');p.stdin.flush()
 apps=rpc(2,'tools/call',{'name':'list_apps','arguments':{}})
 (r/'live-session/probe-apps.json').write_text(json.dumps(apps))
 target=json.loads((r/'live-session/target.json').read_text())
 pid=target['pid'];stat=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split();selector=target['address']+f'@pid={pid}@start={stat[19]}'
 args={'app':'address:'+selector,**json.loads(sys.argv[2])}
 response=rpc(3,'tools/call',{'name':sys.argv[1],'arguments':args})
 (r/'live-session/probe-result.json').write_text(json.dumps(response))
 result=response.get('result',{})
 print('isError:',result.get('isError'))
 for c in result.get('content',[]):
  if c['type']=='text':print(c['text'][:1800])
finally:
 p.stdin.close();p.wait(timeout=10)
