"""Partition sequential MCP runs into non-overlapping measured time categories."""
import json,sys,runpy
from pathlib import Path
from collections import Counter
here=Path(__file__).resolve().parent
classify=runpy.run_path(str(here/'agent-turn-timing.py'))['classify']
phase=here/sys.argv[1]
metrics=json.loads((phase/'metrics.json').read_text())
rows=[]
for task in metrics['tasks']:
 if task.get('running'):continue
 c=Counter()
 for line in (phase/task['id']/'portal.jsonl').read_text().splitlines():
  p=json.loads(line);spans=p['response'].get('result',{}).get('_meta',{}).get('hypr-use/timing',{}).get('spans',[])
  for span in spans:
   ancestors=[span['stage']];parent=span.get('parent');seen=set()
   while parent is not None:
    assert parent not in seen
    seen.add(parent);ancestors.append(spans[parent]['stage']);parent=spans[parent].get('parent')
   if any(x.startswith('atspi_') for x in ancestors):category='Accessibility scans/actions'
   elif 'global_menu_for_window' in ancestors:category='Menu collection'
   elif 'screenshot_for_window' in ancestors:category='Screenshots'
   elif 'finish_related_action_session' in ancestors:category='Action completion / focus guard'
   elif span['stage']=='sleep':category='Explicit waits'
   elif 'call_ctl' in ancestors or 'control_request' in ancestors:category='Input and compositor control'
   else:category='Other instrumented backend'
   c[category]+=span.get('self_ms',0)/1000
 c['Other tool work / internal transport']=task['tool_s']-sum(c.values())
 assert c['Other tool work / internal transport']>=-0.01,c
 turn_buckets,turn_detail=classify(phase/task['id'],task['duration_s'],task['tool_s'])
 c.update(turn_buckets)
 assert abs(sum(c.values())-task['duration_s'])<0.001
 rows.append({'task':task['id'],'duration_s':task['duration_s'],'tool_s':task['tool_s'],'js_calls':task['js_calls'],'screenshots':task['images_emitted'],'refocus':task['refocus'],'review':task['review'],'model_turn_timing':turn_detail,'breakdown':{k:{'seconds':v,'percent':100*v/task['duration_s']} for k,v in c.items()}})
total=sum(x['duration_s'] for x in rows);counts=Counter()
for r in rows:
 for k,v in r['breakdown'].items():counts[k]+=v['seconds']
result={'method':'Nested span self-time assigned once using ancestry. Remaining server time includes uninstrumented work and internal transport. Model-turn gaps include inference, provider waiting and orchestration; not pure inference. Reviewed annotations separate normal, failure-recovery and final-failure-report gaps; unreviewed gaps remain unclassified. Sequential tool execution, single attempt per task.','total_s':total,'tasks':rows,'aggregate':{k:{'seconds':v,'percent':v/total*100} for k,v in counts.most_common()}}
(phase/'breakdown.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
