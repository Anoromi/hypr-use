"""Compare fixed recorded phases without treating failures as speedups."""
import collections
import json
from pathlib import Path
here=Path(__file__).resolve().parent

def supported(r):
    return r.get('verified') is True or (r.get('review') or {}).get('outcome')=='pass'

def summarize(phase):
    data=json.loads((here/phase/'metrics.json').read_text())
    if phase=='astra-fast' and (here/'astra-fast-completion/metrics.json').exists():
        extra=json.loads((here/'astra-fast-completion/metrics.json').read_text());data['tasks']+=extra['tasks'];data['refocus_count']+=extra['refocus_count'];data['focus_coverage']['observer_errors']+=extra['focus_coverage']['observer_errors']
    rows=[r for r in data['tasks'] if not r.get('running') and not r.get('excluded_setup_trial')]
    stages=collections.Counter();counts=collections.Counter();control=collections.Counter()
    for r in rows:
        stages.update(r['stage_self_ms']);counts.update(r['stage_counts']);control.update(r['portal_command_context_ms'])
    return dict(phase=phase,tasks=len(rows),supported=sum(supported(r) for r in rows),wall_s=sum(r['duration_s'] for r in rows),tool_s=sum(r['tool_s'] for r in rows),outside_tools_s=sum(r['non_tool_s'] for r in rows),js_calls=sum(r['js_calls'] for r in rows),images=sum(r['images_emitted'] for r in rows),text_chars=sum(r.get('text_response_chars',0) for r in rows),metadata_chars=sum(r.get('timing_metadata_chars',0) for r in rows),task_timeouts=sum(bool(r.get('timeout')) for r in rows),raw_focus_alarms=data['refocus_count'],confirmed_agent_refocus=(0 if phase=='astra-fast' and (here/phase/'focus-review.json').exists() and data['refocus_count']==1 else data['refocus_count']),observer_errors=len(data['focus_coverage']['observer_errors']),stage_self_s={k:v/1000 for k,v in stages.most_common()},stage_counts=dict(counts),control_context_s={k:v/1000 for k,v in control.most_common()}),rows
old,a=summarize('astra-optimized');new,b=summarize('astra-fast')
byid={r['id']:r for r in a}
pairs=[(byid[r['id']],r) for r in b if r['id'] in byid and supported(r) and supported(byid[r['id']])]
matched={'tasks':[x['id'] for x,y in pairs],'before_s':sum(x['duration_s'] for x,y in pairs),'after_s':sum(y['duration_s'] for x,y in pairs)}
if matched['before_s']:matched['change_pct']=(matched['after_s']/matched['before_s']-1)*100
probes={}
for name in ['probe-results','fast-probe-results']:
    p=here/(name+'.json')
    if p.exists():probes[name]=json.loads(p.read_text())
out={'previous':old,'latest':new,'matched_successes':matched,'probes':probes,'limits':['Single model attempt per task, dependent Calc state, and retained browser tabs.','Outside-tool time includes model generation, startup, scheduling and transport.','call_ctl self time in latest excludes the new control_request child. Sum both for comparable control work.','Control command screenshot time includes Python rendering and PNG processing, not just IPC.','Text and timing metadata character counts are serialized output sizes, not confirmed model token costs.']}
(here/'performance-comparison.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in {'probes','previous','latest'}},indent=2))
for label,record in [('previous',old),('latest',new)]:print(label,{k:v for k,v in record.items() if k not in {'stage_self_s','stage_counts','control_context_s'}})
