"""Classify observable model-turn gaps, using reviewed failure annotations."""
import json
from collections import Counter

def classify(task_dir, duration_s, server_s):
 events=[json.loads(l) for l in (task_dir/'events.jsonl').read_text().splitlines() if l.strip()]
 annotations_path=task_dir/'timing-annotations.json'
 annotations=json.loads(annotations_path.read_text()) if annotations_path.exists() else {}
 pending={};calls=[]
 for event in events:
  item=event['event'].get('item',{})
  if item.get('type')!='mcp_tool_call':continue
  if event['event']['type']=='item.started':pending[item['id']]=event['time']
  elif event['event']['type']=='item.completed' and item['id'] in pending:
   calls.append({'id':item['id'],'title':item.get('arguments',{}).get('title',''),'start':pending.pop(item['id']),'end':event['time']})
 if pending or not calls:
  return {'Outside server tools (unclassified)':duration_s-server_s}, {'status':'Incomplete call intervals; no causal classification attempted'}
 calls.sort(key=lambda c:c['start'])
 assert all(calls[i]['start']>=calls[i-1]['end'] for i in range(1,len(calls))), 'Overlapping MCP calls need interval-union accounting'
 bucket_names={'normal':'Normal task model-turn gaps','failure_recovery':'Failure recovery model-turn gaps','failure_report':'Final failure report model-turn gap','unclassified':'Unclassified model-turn gaps'}
 counts=Counter();segments=[];previous=events[0]['time']
 for c in calls:
  kind=annotations.get('gap_before_call',{}).get(c['id'],'unclassified');assert kind in bucket_names
  gap=c['start']-previous;counts[bucket_names[kind]]+=gap
  segments.append({'before_call':c['id'],'title':c['title'],'seconds':gap,'category':kind});previous=c['end']
 kind=annotations.get('after_last_call','unclassified');assert kind in bucket_names
 gap=events[-1]['time']-previous;counts[bucket_names[kind]]+=gap
 segments.append({'after_last_call':calls[-1]['id'],'seconds':gap,'category':kind})
 counts['CLI lifecycle outside event recording']=duration_s-(events[-1]['time']-events[0]['time'])
 counts['MCP overhead outside server handler']=sum(c['end']-c['start'] for c in calls)-server_s
 assert all(v>=-0.01 for v in counts.values()),counts
 assert abs(sum(counts.values())-(duration_s-server_s))<0.001
 return dict(counts), {'status':'Classified from received event timestamps','annotations':annotations,'segments':segments,'limitation':'Model-turn gaps include inference, provider waiting and orchestration. They are not isolated inference measurements. Failure classification is reviewed, not inferred merely from tool error flags. Unreviewed gaps remain unclassified.'}
