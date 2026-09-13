"""Compare full independent phases without substituting development retries."""
import collections,json,statistics
from pathlib import Path
here=Path(__file__).resolve().parent
def read(phase):return {r['id']:r for p in (here/'runs'/phase).glob('*/summary.json') if (r:=json.loads(p.read_text()))}
old=read('baseline-v2');new=read('improved-v1');complete=len(old)==len(new)==50 and set(old)==set(new)
result={'baseline':'baseline-v2','improved':'improved-v1','complete':complete,'baseline_completed':len(old),'improved_completed':len(new),'note':'Only these two phases enter the comparison. Development retries and the aborted setup run remain separate.'}
if complete:
 manifests=[json.loads((here/'runs'/phase/'manifest.json').read_text()) for phase in ['baseline-v2','improved-v1']]
 assert manifests[0]['catalog']==manifests[1]['catalog']
 assert all(manifests[0][k]==manifests[1][k] for k in ['model','effort'])
 assert all(digest==manifests[1]['source_hashes'][path] for path,digest in manifests[0]['source_hashes'].items() if path.startswith('testing/'))
 assert all(r.get('source_unchanged') for r in [*old.values(),*new.values()])
 result['verification']={'same_tasks':True,'same_model_and_effort':True,'same_benchmark_harness':True,'runtime_frozen_within_each_phase':True,'initial_states_failed_grading':all(not json.loads((here/'runs'/phase/task/'initial-grade.json').read_text())['passed'] for phase in ['baseline-v2','improved-v1'] for task in old)}
 audits=[json.loads((here/'runs'/phase/'output-audit.json').read_text()) for phase in ['baseline-v2','improved-v1']]
 assert all(a['audited']==15 and not a['new_disagreements'] for a in audits),'Stronger output checks need review'
 result['verification']['stronger_output_checks_agree_with_scored_passes']=True
 result['fixed']=[k for k in old if old[k]['outcome']=='fail' and new[k]['outcome']=='pass']
 result['regressions']=[k for k in old if old[k]['outcome']=='pass' and new[k]['outcome']!='pass']
 result['still_failed']=[k for k in old if old[k]['outcome']!='pass' and new[k]['outcome']!='pass']
 result['groups']={}
 for group in ['native','navigation','web','calc','writer']:
  result['groups'][group]={}
  for label,rows in [('baseline',old),('improved',new)]:
   rr=[r for r in rows.values() if r['group']==group];result['groups'][group][label]={'passed':sum(r['outcome']=='pass' for r in rr),'failed':sum(r['outcome']!='pass' for r in rr),'agent_s':sum(r['duration_s'] for r in rr)}
 result['totals']={}
 for label,rows in [('baseline',old),('improved',new)]:
  rr=list(rows.values());failed=sum(r['outcome']!='pass' for r in rr)
  result['totals'][label]={'passed':50-failed,'failed':failed,'failure_percent':failed*2,'agent_s':sum(r['duration_s'] for r in rr),'median_task_s':statistics.median(r['duration_s'] for r in rr),'provider_failures':sum(bool(r.get('provider_errors')) for r in rr),'refocuses':sum(bool(r.get('refocus')) for r in rr)}
 passed_both=[k for k in old if old[k]['outcome']==new[k]['outcome']=='pass']
 result['passed_in_both']={'tasks':len(passed_both),'baseline_s':sum(old[k]['duration_s'] for k in passed_both),'improved_s':sum(new[k]['duration_s'] for k in passed_both)}
 result['task_pairs']=[{'id':k,'baseline':old[k]['outcome'],'improved':new[k]['outcome'],'baseline_s':old[k]['duration_s'],'improved_s':new[k]['duration_s']} for k in sorted(old)]
(here/'comparison.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='task_pairs'},indent=2))
