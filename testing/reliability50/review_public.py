"""Conservative offline review: a URL alone does not prove a public page loaded."""
import json,sys
from pathlib import Path
here=Path(__file__).resolve().parent;p=here/'runs'/sys.argv[1];rows=[]
expected={'11-google':['Google Search','Search Google'],'12-example':['Example Domain'],'13-wikipedia':['Ada Lovelace'],'14-iana':['Example Domains'],'15-python':['Python']}
for task,terms in expected.items():
 d=p/task;wire=d/task/'wire.jsonl'
 if not (d/'summary.json').exists():continue
 summaries=[]
 portal=d/task/'portal.jsonl'
 if portal.exists():
  for l in portal.read_text().splitlines():
   v=json.loads(l);r=v.get('response',{}).get('result',{}).get('structuredContent',{})
   if r.get('observationDeferred'):continue
   if r.get('treeLines'):summaries.append({'window':r.get('windowTitle'),'tree':'\n'.join(r['treeLines'])})
 # Candidate evidence for a reviewer. Keep this distinct from automatic grading;
 # stale trees and browser chrome text can otherwise create false positives.
 evidence=[s for s in summaries if any(t.lower() in s['tree'].lower() for t in terms)]
 rows.append({'task':task,'observation_candidates':evidence[-2:],'status':'needs_review','url_grade':json.loads((d/'grade.json').read_text()) if (d/'grade.json').exists() else None})
(p/'public-review.json').write_text(json.dumps(rows,indent=2));print([(r['task'],len(r['observation_candidates'])) for r in rows])
