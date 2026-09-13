"""Audit recorded starting messages and tool use without copying private rollout content."""
import json,sys,hashlib
from pathlib import Path
here=Path(__file__).resolve().parent
for phase in sys.argv[1:]:
 p=here/phase;d=p/'restore-last-tab';events=[json.loads(l) for l in (d/'events.jsonl').read_text().splitlines()]
 tid=next(e['event']['thread_id'] for e in events if e['event']['type']=='thread.started')
 f=next(Path('/home/anoromi/.codex/sessions').rglob('*'+tid+'*.jsonl'))
 messages=[];tool_calls=[];usage=None
 for line in f.read_text().splitlines():
  r=json.loads(line);v=r.get('payload',{})
  if r['type']=='response_item' and v.get('type')=='message' and v.get('role') in ['user','developer','system']:
   s=json.dumps(v);messages.append({'role':v['role'],'chars':len(s),'sha256':hashlib.sha256(s.encode()).hexdigest(),'target_name_present':'tripadvisor' in s.lower(),'previous_result_terms_present':any(x in s for x in ['42.65','141.6','22.30','astra-restore-fixed','astra-published-restore'])})
  if r['type']=='response_item' and v.get('type') in ['custom_tool_call','function_call']:tool_calls.append({'name':v.get('name'),'input':v.get('input',v.get('arguments',''))})
  if v.get('type')=='token_count' and v.get('info'):usage=v['info'].get('total_token_usage')
 setup=json.loads((p/'setup.json').read_text())
 out={'thread_id':tid,'messages':messages,'tool_calls':tool_calls,'usage':usage,'restore_preflight':setup.get('restore_preflight','legacy setup: preflight present'),'initial_tabs':[x['url'] for x in json.loads((p/'tabs-start.json').read_text())],'limits':'Checks recorded context and calls, not provider internals. Cached prompt tokens do not by themselves establish previous conversation leakage.'}
 (p/'context-audit.json').write_text(json.dumps(out,indent=2));print(phase,tid,'starting target/history terms',any(x['target_name_present'] or x['previous_result_terms_present'] for x in messages),'tool calls',len(tool_calls))
