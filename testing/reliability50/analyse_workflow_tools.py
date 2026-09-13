"""Summarize explicit MCP workflow adoption and recorded outcomes."""
import collections,json
from pathlib import Path
here=Path(__file__).resolve().parent
rows=[]
for phase in ['workflow-tools-v1','workflow-tools-v2']:
 manifest=json.loads((here/'runs'/phase/'manifest.json').read_text())
 assert manifest['model']=='gpt-6-astra' and manifest['effort']=='xhigh'
 for d in sorted((here/'runs'/phase).iterdir()):
  if not (d/'summary.json').exists():continue
  r=json.loads((d/'summary.json').read_text());calls=[]
  for line in (d/d.name/'wire.jsonl').read_text().splitlines():
   v=json.loads(line);calls.append({'name':v['request']['params']['name'],'error':v['response']['result'].get('isError',False),'milliseconds':v['response']['result'].get('_meta',{}).get('hypr-use/timing',{}).get('total_ms')})
  rows.append({'phase':phase,'id':r['id'],'passed':r['outcome']=='pass','seconds':r['duration_s'],'refocus':r['refocus'],'source_unchanged':r['source_unchanged'],'calls':calls})
result={'model':'gpt-6-astra','effort':'xhigh','rows':rows,'direct_tool_calls':dict(collections.Counter(c['name'] for r in rows for c in r['calls'])),'notes':'Fresh owned apps, fresh CLI threads, independent grades and foreground monitoring. Exploratory adoption tests, not a paired performance benchmark. V2 removes a redundant navigation click and emits the exact matched wait snapshot. No table tool.'}
(here/'workflow-tool-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'completed':len(rows),'passed':sum(r['passed'] for r in rows),'refocus':sum(r['refocus'] for r in rows),'tools':result['direct_tool_calls']},indent=2))
