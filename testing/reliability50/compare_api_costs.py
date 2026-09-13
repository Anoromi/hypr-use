"""Compare focused phases without substituting previous full-suite results."""
import json,collections
from pathlib import Path
here=Path(__file__).resolve().parent
phases=['api-cost-before','api-cost-after']
rows=[]
for phase in phases:
 manifest=json.loads((here/'runs'/phase/'manifest.json').read_text())
 assert manifest['model']=='gpt-6-astra' and manifest['effort']=='xhigh'
 for d in sorted((here/'runs'/phase).iterdir()):
  if not (d/'summary.json').exists():continue
  row=json.loads((d/'summary.json').read_text());stages=collections.Counter();handlers=0;operations=collections.defaultdict(list)
  for line in (d/d.name/'portal.jsonl').read_text().splitlines():
   v=json.loads(line);seconds=v['duration_ms']/1000;handlers+=seconds;operations[v['request']['params']['name']].append(seconds)
   for span in v.get('response',{}).get('result',{}).get('_meta',{}).get('hypr-use/timing',{}).get('spans',[]):stages[span['stage']]+=span.get('self_ms',0)/1000
  wire=[json.loads(l) for l in (d/d.name/'wire.jsonl').read_text().splitlines()]
  rows.append(dict(phase=phase,id=row['id'],passed=row['outcome']=='pass',refocus=row['refocus'],source_unchanged=row['source_unchanged'],agent_s=row['duration_s'],handler_s=handlers,menu_s=stages['global_menu_for_window'],js_calls=len(wire),tool_errors=sum(bool(v.get('response',{}).get('result',{}).get('isError')) for v in wire),operations=operations))
assert all(len([r for r in rows if r['phase']==p])==3 for p in phases),'Both targeted phases must complete'
a,b=[json.loads((here/'runs'/p/'manifest.json').read_text()) for p in phases]
assert a['catalog']==b['catalog']
changed=[p for p in a['source_hashes'] if a['source_hashes'][p]!=b['source_hashes'].get(p)]
assert changed==['mcp/unified/observations.py'],changed
result={'baseline_commit':'9ef2795','changed_runtime_files':changed,'rows':rows,'limitations':'One fresh Astra run per task per phase. Workflow and provider timing vary; use the controlled observation and keyboard probes for isolated action costs. No full-suite rerun.'}
(here/'api-performance.json').write_text(json.dumps(result,indent=2)+'\n')
for r in rows:print(r['phase'],r['id'],r['passed'],round(r['agent_s'],2),round(r['handler_s'],2),r['js_calls'],r['tool_errors'])
