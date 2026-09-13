"""Build a self-contained report from recorded benchmark phases."""
import html,json,sys,os
from pathlib import Path
here=Path(__file__).resolve().parent
phases=sys.argv[1:] or ['astra-baseline','astra-optimized']
e=html.escape
sections=[]
loaded={}
for phase in phases:
 p=here/phase/'metrics.json'
 if not p.exists():continue
 data=json.loads(p.read_text());loaded[phase]=data;rows=[];details=[]
 for r in data['tasks']:
  task=r['id'];status='Running' if r.get('running') else 'Verified pass' if r.get('verified') is True else 'Verified fail' if r.get('verified') is False else 'Not independently verified'
  if (r.get('review') or {}).get('outcome') in {'pass','fail'}:status='Reviewed '+r['review']['outcome']
  if r.get('excluded_setup_trial'):status='Excluded setup trial'
  if r.get('timeout'):status+='; timed out'
  duration=r.get('duration_s',0);tool=r.get('tool_s',0)
  rows.append(f'<tr><td><a href="#{e(phase+task)}">{e(task)}</a></td><td>{e(status)}</td><td>{duration:.1f}</td><td>{tool:.1f}</td><td>{r.get("js_calls",0)}</td><td>{r.get("images_emitted",0)}</td><td>{len(r.get("failures",[]))}</td></tr>')
  stages=sorted(r.get('stage_self_ms',{}).items(),key=lambda x:-x[1]);stage_rows=''.join(f'<tr><td>{e(k)}</td><td>{v/1000:.3f}</td></tr>' for k,v in stages)
  d=here/phase/task;calls=[]
  if (d/'wire.jsonl').exists():
   for line in (d/'wire.jsonl').read_text().splitlines():
    try:w=json.loads(line)
    except ValueError:continue
    req=w['request'].get('params',{});result=w['response'].get('result',{});args=req.get('arguments',{});ms=result.get('_meta',{}).get('hypr-use/timing',{}).get('total_ms',0)
    outputs=[]
    for b in result.get('content',[]):
     if b.get('type')=='text':outputs.append('<pre>'+e(b.get('text',''))+'</pre>')
     elif b.get('type')=='image':outputs.append('<img loading="lazy" alt="Recorded agent screenshot" src="data:'+e(b.get('mimeType','image/png'))+';base64,'+e(b['data'])+'">')
    timings=[]
    for operation in result.get('_meta',{}).get('hypr-use/timing',{}).get('operations',[]):
     spans=operation.get('backend',{}).get('spans',[]) if operation.get('backend') else []
     timings.append('<h4>'+e(operation['name'])+f' · {operation["duration_ms"]/1000:.3f}s</h4><table><tr><th>Backend stage</th><th>Total ms</th><th>Self ms</th></tr>'+''.join(f'<tr><td>{e(span["stage"])}</td><td>{span.get("duration_ms",0):.2f}</td><td>{span.get("self_ms",0):.2f}</td></tr>' for span in spans)+'</table>')
    outputs.append('<details><summary>Internal timings</summary>'+(''.join(timings) or '<p>No completed operation timings returned. Baseline timeouts lost outer operation details; completed portal responses remain in the repository recording.</p>')+'</details>')
    calls.append(f'<details><summary>{e(args.get("title") or req.get("name","tool"))} · {ms/1000:.3f}s'+(' · Error' if result.get('isError') else '')+'</summary><pre>'+e(args.get('code',json.dumps(args)))+'</pre>'+''.join(outputs)+'</details>')
  details.append(f'<section id="{e(phase+task)}"><h3>{e(task)}</h3><p>{e(status)}. Total {duration:.1f}s; tool execution {tool:.1f}s; other elapsed time {r.get("non_tool_s",0):.1f}s.</p><p>Agent report: {e(r.get("final", "Pending"))}</p><details><summary>Outcome review</summary><pre>{e(json.dumps(r.get('review'),indent=2))}</pre></details><p>Observation API calls: {e(json.dumps({k:v for k,v in r.get('methods',{}).items() if k in ['getApp','getAXState','getScreenshot','getAXStateAndScreenshot']}))}. Input targeting: {e(json.dumps(r.get('input_targeting',{})))}. Reported completed dispatch methods: {e(json.dumps(r.get('reported_dispatch_methods',{})))}. AX-index targeting may use a guarded pointer fallback; this does not count as pure AT-SPI input.</p><details><summary>Backend stage self-time</summary><table><tr><th>Stage</th><th>Seconds</th></tr>{stage_rows}</table></details>'+''.join(calls)+'</section>')
 sections.append(f'<section><h2>{e(phase)}</h2><p>{data["completed"]} attempts recorded. {data["verified_pass"]} independently passed, {data["verified_fail"]} independently failed. {data["refocus_count"]} raw focus alarms. See the focus review for any address-reuse false positives. {data.get('reviewed_pass',0)} reviewed passes.</p><details><summary>Focus monitor coverage</summary><pre>{e(json.dumps(data.get('focus_coverage',{}),indent=2))}</pre></details><div class="scroll"><table><thead><tr><th>Task</th><th>Evidence</th><th>Total s</th><th>Tool s</th><th>JS calls</th><th>Images</th><th>Errors</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'+''.join(details)+'</section>')
def successful(r):return r.get('verified') is True or (r.get('review') or {}).get('outcome')=='pass'
def label(r):return 'Automatic pass' if r.get('verified') is True else 'Reviewed pass' if (r.get('review') or {}).get('outcome')=='pass' else 'Reviewed fail' if (r.get('review') or {}).get('outcome')=='fail' else 'Failed check' if r.get('verified') is False else 'Timed out' if r.get('timeout') else 'Unverified'
baseline=[r for phase,data in loaded.items() if phase in ['astra-baseline','astra-baseline-calc'] for r in data['tasks'] if not r.get('excluded_setup_trial') and not r.get('running')]
optimized=[r for r in loaded.get('astra-optimized',{}).get('tasks',[]) if not r.get('running')]
base={r['id']:r for r in baseline};pairs=[(base[r['id']],r) for r in optimized if r['id'] in base]
comparison='<h2>Before and after</h2><p>'+str(len(baseline))+' baseline tasks and '+str(len(optimized))+' optimized tasks completed. Tasks with completion evidence: '+str(sum(successful(r) for r in baseline))+' baseline, '+str(sum(successful(r) for r in optimized))+' optimized.</p>'
comparison+='<table><tr><th>All attempts</th><th>Wall s</th><th>Tool s</th><th>Images captured</th><th>Images emitted</th><th>Task timeouts</th></tr>'+''.join(f'<tr><td>{name}</td><td>{sum(r["duration_s"] for r in rows):.1f}</td><td>{sum(r["tool_s"] for r in rows):.1f}</td><td>{sum(r.get("stage_counts",{}).get("screenshot_for_window",0) for r in rows)}</td><td>{sum(r["images_emitted"] for r in rows)}</td><td>{sum(bool(r.get("timeout")) for r in rows)}</td></tr>' for name,rows in [('Baseline',baseline),('Optimized',optimized)])+'</table>'
matched=[(a,b) for a,b in pairs if successful(a) and successful(b)]
if matched:
 old=sum(a['duration_s'] for a,b in matched);new=sum(b['duration_s'] for a,b in matched)
 comparison+=f'<p>For the {len(matched)} tasks supported as successful in both runs: {old:.1f}s before, {new:.1f}s after. Change: {(new/old-1)*100:+.1f}%. These are single runs, not a statistical confidence estimate.</p>'
comparison+='<p>All-attempt timings include failures and extra recovery. An early failure can finish quickly; compare outcome evidence alongside duration. Baseline setup trials are excluded. Browser tab inventory grew between phases; both retain the user’s existing many-tab Zen session.</p><div class="scroll"><table><tr><th>Task</th><th>Before s</th><th>After s</th><th>Tool before s</th><th>Tool after s</th><th>Before evidence</th><th>After evidence</th></tr>'+''.join(f'<tr><td>{e(a["id"])}</td><td>{a["duration_s"]:.1f}</td><td>{b["duration_s"]:.1f}</td><td>{a["tool_s"]:.1f}</td><td>{b["tool_s"]:.1f}</td><td>{label(a)}</td><td>{label(b)}</td></tr>' for a,b in pairs)+'</table></div>'
fast=[r for phase in ['astra-fast','astra-fast-completion'] for r in loaded.get(phase,{}).get('tasks',[]) if not r.get('running') and not r.get('excluded_setup_trial')]
if fast:
 old_by_id={r['id']:r for r in optimized}
 fast_pairs=[(old_by_id[r['id']],r) for r in fast if r['id'] in old_by_id]
 supported=[(a,b) for a,b in fast_pairs if successful(a) and successful(b)]
 latest='<h2>Fixed 24-task performance comparison</h2><p>'+str(len(fast))+' of 24 new attempts recorded; '+str(sum(successful(r) for r in fast))+' have completion evidence. The preceding optimized run had 20 of 24 supported outcomes, including a sorting state pass whose process timed out.</p>'
 latest+='<table><tr><th>Phase</th><th>Total s</th><th>Tool s</th><th>JS calls</th><th>Task timeouts</th></tr>'+''.join(f'<tr><td>{name}</td><td>{sum(r["duration_s"] for r in rows):.1f}</td><td>{sum(r["tool_s"] for r in rows):.1f}</td><td>{sum(r["js_calls"] for r in rows)}</td><td>{sum(bool(r.get("timeout")) for r in rows)}</td></tr>' for name,rows in [('Previous optimized',optimized),('Latest',fast)])+'</table>'
 if supported:
  old=sum(a['duration_s'] for a,b in supported);new=sum(b['duration_s'] for a,b in supported)
  latest+=f'<p>For {len(supported)} tasks with completion evidence in both phases: {old:.1f}s before and {new:.1f}s after, {(new/old-1)*100:+.1f}%. Single attempts, dependent Calc state and retained browser tabs limit causal attribution.</p>'
 latest+='<table><tr><th>Task</th><th>Previous s</th><th>Latest s</th><th>Previous tool s</th><th>Latest tool s</th><th>Previous evidence</th><th>Latest evidence</th></tr>'+''.join(f'<tr><td>{e(a["id"])}</td><td>{a["duration_s"]:.1f}</td><td>{b["duration_s"]:.1f}</td><td>{a["tool_s"]:.1f}</td><td>{b["tool_s"]:.1f}</td><td>{label(a)}</td><td>{label(b)}</td></tr>' for a,b in fast_pairs)+'</table>'
 comparison=latest+comparison
extras=''
for filename,title in [('readiness/ax-replay.json','AX output replay'),('readiness/probe-review.json','Browser readiness experiments'),('readiness/metadata-review.json','Timing metadata in Codex recordings'),('probe-results.json','Previous repeated direct tool timings'),('fast-probe-results.json','Latest repeated direct tool timings'),('performance-comparison.json','Detailed performance comparison'),('native-screen-results.json','Native screenshot timings after fixed comparison'),('resize-profile.json','Offline resize profile'),('validation/key-routing-comparison/review.json','Keyboard routing probe'),('astra-fast-save-retry/ods-review.json','Independent saved workbook verification'),('astra-fast/focus-review.json','Review of the monitor false positive'),('astra-save-recovery/ods-verification.json','Workbook checks after separate Save recovery')]:
 source=here/filename
 if source.exists():extras+='<h2>'+title+'</h2><pre>'+e(source.read_text())+'</pre>'
if os.environ.get('HYPR_USE_REPORT_FOCUSED'):
 comparison='';extras=''
 for phase in phases:
  bp=here/phase/'breakdown.json'
  if bp.exists():
   b=json.loads(bp.read_text())
   extras+='<h2>Time breakdown</h2><p>'+e(b['method'])+'</p><table><tr><th>Category</th><th>Seconds</th><th>Share of elapsed time</th></tr>'+''.join(f'<tr><td>{e(k)}</td><td>{v["seconds"]:.2f}</td><td>{v["percent"]:.2f}%</td></tr>' for k,v in b['aggregate'].items())+'</table><details><summary>Per-task breakdown data</summary><pre>'+e(bp.read_text())+'</pre></details>'
notes_path=Path(os.environ.get('HYPR_USE_REPORT_FINDINGS',str(here/'findings.md')))
notes=notes_path.read_text() if notes_path.exists() else 'Baseline in progress. Performance review and comparison are pending.'
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Hypr-use computer-use benchmark</title><style>
body{font:16px/1.5 ui-sans-serif,system-ui;background:#faf8f5;color:#292524;margin:0}main{max-width:1200px;margin:auto;padding:24px}h1{font-size:28px}h2{font-size:23px;margin-top:40px}h3{font-size:18px}a{color:#92400e}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:8px;border-bottom:1px solid #d6d3d1;vertical-align:top}th{font-weight:600}section{margin:24px 0}section section{border-top:1px solid #d6d3d1;padding-top:16px}details{margin:12px 0;border:1px solid #d6d3d1;padding:8px 12px;background:#fff}summary{cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.5 ui-monospace,monospace}img{max-width:100%;height:auto}.scroll{overflow:auto}p{max-width:90ch}
</style><main><h1>Hypr-use computer-use benchmark</h1><p>Separate Codex CLI instances, gpt-6-astra, high reasoning. Native background windows on the user's Hyprland desktop. Each task has a 180-second limit and a prompt limit of 12 JavaScript calls.</p><p>Refocus means an agent target becomes the foreground window. Monitoring combines compositor events and 100 ms polling. Temporary rules suppress initial focus and activation for the fixture and private Calc windows on workspace 902. Zen uses its existing workspace. Zero detected events is evidence for these runs, not a universal guarantee.</p><p>Fixture checks inspect the app's saved state. Web answers and intermediate Calc tasks need separate evidence review; an agent's success claim is not an independent pass. Stage self-times exclude nested spans to avoid double counting. Other elapsed time includes model generation, startup and transport; it is not pure reasoning time. Earlier phases sometimes captured screenshots internally without emitting images. The latest adapter separates AX-only, screenshot-only and combined observations.</p><p><a href="setup.txt">Server setup and supported methods</a> · <a href="reference-api.d.ts">Inspected reference API declarations</a> · <a href="benchmark.ods">Verified workbook from the latest Save retry</a></p><h2>Findings</h2><pre>'''+e(notes)+'</pre>'+comparison+extras+''.join(sections)+'</main></html>'
if os.environ.get('HYPR_USE_REPORT_FOCUSED'):
 page=page.replace(' · <a href="benchmark.ods">Verified workbook from the latest Save retry</a>','')
out=Path(os.environ.get('HYPR_USE_REPORT_OUTPUT','/home/anoromi/Artifacts/hypr-use-unified-benchmark'));out.mkdir(parents=True,exist_ok=True);(out/'index.html').write_text(page);print(out/'index.html')
