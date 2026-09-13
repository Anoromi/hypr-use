"""Non-overlapping wall-time buckets; agent gaps are not pure inference timings."""
import collections,json,sys
from pathlib import Path
from timing_alignment import aligned_calls
here=Path(__file__).resolve().parent;phase=sys.argv[1];directory=here/'runs'/phase
review=json.loads((here/'failure-gap-review.json').read_text());manual=review['phases'].get(phase,{})
rows=[]
for file in sorted(directory.glob('*/summary.json')):
 r=json.loads(file.read_text());d=file.parent/r['id']
 if 'duration_s' not in r:continue
 events=[json.loads(l) for l in (d/'events.jsonl').read_text().splitlines()]
 wire=[json.loads(l) for l in (d/'wire.jsonl').read_text().splitlines()]
 pending={};calls=[]
 for event in events:
  e=event['event'];item=e.get('item',{})
  if item.get('type')!='mcp_tool_call':continue
  if e['type']=='item.started':pending[item['id']]=(event['time'],item)
  elif e['type']=='item.completed' and item['id'] in pending:
   start,initial=pending.pop(item['id']);calls.append({'start':start,'end':event['time'],'code':initial.get('arguments',{}).get('code'),'arguments':initial.get('arguments',{}),'tool':initial.get('tool')})
 aligned=aligned_calls(calls,wire)
 if not aligned or pending:
  rows.append({'id':r['id'],'duration_s':r['duration_s'],'status':'unresolved event/wire alignment'});continue
 failed_gaps=set(manual.get(r['id'],{}).get('gaps',[]));explicit=[]
 for i,w in enumerate(wire):
  if w.get('response',{}).get('result',{}).get('isError'):failed_gaps.update([i,i+1]);explicit.append(i)
 assert all(0<=i<=len(calls) for i in failed_gaps),r['id']
 previous=events[0]['time'];gaps=[]
 for c in calls:gaps.append(c['start']-previous);previous=c['end']
 gaps.append(events[-1]['time']-previous)
 assert min(gaps,default=0)>=-.01,r['id']
 mcp=sum(c['end']-c['start'] for c in calls)
 portal=[json.loads(l) for l in (d/'portal.jsonl').read_text().splitlines()]
 server=sum(v.get('duration_ms',0)/1000 for v in portal)
 buckets={'backend_handlers':server,'mcp_js_overhead':mcp-server,'failure_associated_agent_gaps':sum(g for i,g in enumerate(gaps) if i in failed_gaps),'other_or_uncertain_agent_gaps':sum(g for i,g in enumerate(gaps) if i not in failed_gaps),'startup_teardown_and_unobserved':r['duration_s']-mcp-sum(gaps)}
 assert min(buckets.values())>=-.05,(r['id'],buckets)
 assert abs(sum(buckets.values())-r['duration_s'])<.001
 rows.append({'id':r['id'],'duration_s':r['duration_s'],'status':'aligned','buckets_s':buckets,'explicit_error_calls':explicit,'failure_gap_indices':sorted(failed_gaps),'gaps_s':gaps,'review':manual.get(r['id'])})
total=collections.Counter()
for r in rows:total.update(r.get('buckets_s',{}))
seconds=sum(total.values());result={'phase':phase,'tasks':len(rows),'aligned':sum(r['status']=='aligned' for r in rows),'method':review['method'].replace('JS call','MCP call'),'limitation':'Agent gaps combine inference, provider waiting and CLI orchestration. This is a reviewed lower-bound classification of failure-associated gaps, not direct inference telemetry. Tool and overhead time remain separate even for failed actions. Setup time is outside the agent-run duration.','total_s':seconds,'buckets_s':dict(total),'buckets_percent':{k:v/seconds*100 for k,v in total.items()} if seconds else {},'rows':rows}
(directory/'timing-breakdown.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
