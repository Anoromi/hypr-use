"""Inspect existing traces only; never touches running app state."""
import collections,json,sys
from pathlib import Path
here=Path(__file__).resolve().parent;p=here/'runs'/sys.argv[1];rows=[]
for d in sorted(p.iterdir()):
 if not d.is_dir() or not (d/'summary.json').exists():continue
 r=json.loads((d/'summary.json').read_text());events=d/d.name/'events.jsonl';wire=d/d.name/'wire.jsonl';portal=d/d.name/'portal.jsonl'
 r['calls']=[];r['ax_statuses']=collections.Counter();r['tool_s']=0;r['stages_s']=collections.Counter()
 if wire.exists():
  for line in wire.read_text().splitlines():
   v=json.loads(line);res=v.get('response',{}).get('result',{});r['calls'].append({'code':v['request']['params'].get('arguments',{}).get('code'),'error':res.get('isError',False),'images':sum(c.get('type')=='image' for c in res.get('content',[])),'error_text':'\n'.join(c.get('text','') for c in res.get('content',[]) if c.get('type')=='text') if res.get('isError') else ''})
 if portal.exists():
  for line in portal.read_text().splitlines():
   v=json.loads(line);r['tool_s']+=v.get('duration_ms',0)/1000;res=v.get('response',{}).get('result',{});state=res.get('structuredContent',{});status=state.get('accessibility',{}).get('status')
   if status:r['ax_statuses'][status]+=1
   for span in res.get('_meta',{}).get('hypr-use/timing',{}).get('spans',[]):r['stages_s'][span['stage']]+=span.get('self_ms',0)/1000
 if events.exists():
  es=[json.loads(l) for l in events.read_text().splitlines()];pending={};calls=[]
  for e in es:
   i=e['event'].get('item',{})
   if i.get('type')!='mcp_tool_call':continue
   if e['event']['type']=='item.started':pending[i['id']]=e['time']
   elif e['event']['type']=='item.completed' and i['id'] in pending:calls.append({'id':i['id'],'start':pending.pop(i['id']),'end':e['time']})
  last=es[0]['time'];r['gaps']=[]
  for c in calls:r['gaps'].append({'before':c['id'],'seconds':c['start']-last,'classification':'unreviewed'});last=c['end']
  r['gaps'].append({'before':'final','seconds':es[-1]['time']-last,'classification':'unreviewed'})
 r['final']=(d/d.name/'final.txt').read_text() if (d/d.name/'final.txt').exists() else '';rows.append(r)
(p/'analysis.json').write_text(json.dumps(rows,indent=2))
print(json.dumps({'completed':len(rows),'outcomes':dict(collections.Counter(r['outcome'] for r in rows)),'failures':[{'id':r['id'],'outcome':r['outcome'],'failure_kind':r.get('failure_kind'),'final':r['final'][:220]} for r in rows if r['outcome']!='pass'],'ax_statuses':dict(sum((r['ax_statuses'] for r in rows),collections.Counter()))},indent=2))
