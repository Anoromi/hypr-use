import collections,html,json,time,sys,subprocess
from pathlib import Path
from catalog import catalog
here=Path(__file__).resolve().parent;out=Path('/home/anoromi/Artifacts/hypr-use-reliability50');out.mkdir(exist_ok=True)
def shared_text(value):
 try:parsed=json.loads(value)
 except (ValueError,TypeError):return value
 if isinstance(parsed,list) and any(isinstance(v,dict) and 'displayName' in v and 'isRunning' in v for v in parsed):return '[Desktop app inventory omitted from shared report; full trace remains local.]'
 return value
def build():
 phases=[]
 for phase in sorted((here/'runs').glob('*')):
  if not phase.is_dir():continue
  rows=[]
  for task in catalog():
   d=phase/task['id'];p=d/'summary.json'
   if not p.exists():continue
   r=json.loads(p.read_text());r['prompt']=task['prompt'];r['tool_errors']=[];r['js_calls']=0;r['images']=0;r['tool_s']=0
   wire=d/task['id']/'wire.jsonl'
   if wire.exists():
    for line in wire.read_text().splitlines():
     v=json.loads(line);res=v.get('response',{}).get('result',{});r['js_calls']+=1;r['images']+=sum(c.get('type')=='image' for c in res.get('content',[]))
     if res.get('isError'):r['tool_errors'].append({'code':v['request']['params'].get('arguments',{}).get('code'),'error':'\n'.join(shared_text(c.get('text','')) for c in res.get('content',[]) if c.get('type')=='text')})
   portal=d/task['id']/'portal.jsonl'
   if portal.exists():r['tool_s']=sum(json.loads(l).get('duration_ms',0)/1000 for l in portal.read_text().splitlines())
   f=d/task['id']/'final.txt';r['final']=f.read_text() if f.exists() else ''
   events=d/task['id']/'events.jsonl'
   if events.exists():
    ee=[json.loads(l)['event'] for l in events.read_text().splitlines()]
    r['provider_errors']=[v.get('message',v.get('error',{}).get('message','')) for v in ee if v.get('type') in ['error','turn.failed']]
    if r['provider_errors']:r['failure_kind']='provider'
   if (d/'grade.json').exists():r['grade']=json.loads((d/'grade.json').read_text())
   if (d/'review.json').exists():r['review']=json.loads((d/'review.json').read_text())
   if (d/'output-audit.json').exists():r['output_audit']=json.loads((d/'output-audit.json').read_text())
   rows.append(r)
  phases.append({'phase':phase.name,'rows':rows})
 (out/'results.json').write_text(json.dumps(phases,indent=2));(out/'tasks.json').write_text(json.dumps(catalog(),indent=2))
 parts=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>50-task background reliability</title><style>body{font:16px system-ui;line-height:1.5;max-width:1100px;margin:32px auto;padding:0 20px;color:#222}h1{font-size:28px}h2{font-size:22px}table{width:100%;border-collapse:collapse}td,th{text-align:left;vertical-align:top;padding:9px;border-bottom:1px solid #ddd}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#1659a5}details{margin:16px 0}</style><body><h1>50-task background reliability</h1><p>Five groups of ten independently prepared tasks. GPT-6 Astra xhigh, fresh CLI thread and app profile for each task, unified JS MCP, 240-second timeout. Runs take place on the user’s desktop in background workspace 902. A detected refocus stops execution.</p><p>This is a custom suite, not a published benchmark. Five tasks visit public websites; the remaining tasks use local state. Pilot results are excluded from the 50-task baseline. Incomplete phases are interim results and should not be treated as the final failure rate.</p><p><a href="tasks.json">All 50 task definitions and evaluators</a> · <a href="results.json">Measured results and error evidence</a></p>']
 comparison=here/'comparison.json'
 if comparison.exists():
  summary=json.loads(comparison.read_text());(out/'comparison.json').write_text(json.dumps(summary,indent=2))
  if summary.get('complete'):
   before=summary['totals']['baseline'];after=summary['totals']['improved']
   parts.append(f'<h2>Completed paired comparison</h2><p>Failure rate: {before["failed"]}/50 ({before["failure_percent"]:.0f}%) before, {after["failed"]}/50 ({after["failure_percent"]:.0f}%) after. {len(summary["fixed"])} original failures passed; {len(summary["regressions"])} previously passing tasks regressed.</p><p>Agent-run time across all 50 attempts: {before["agent_s"]/60:.1f} minutes before and {after["agent_s"]/60:.1f} minutes after. These are observed times, not an isolated causal estimate of each fix. <a href="comparison.json">Paired results and verification</a>.</p><table><tr><th>Category</th><th>Baseline failures</th><th>Improved failures</th></tr>')
   for group,r in summary['groups'].items():parts.append(f'<tr><td>{group}</td><td>{r["baseline"]["failed"]}/10</td><td>{r["improved"]["failed"]}/10</td></tr>')
   parts.append('</table><p>One fresh attempt per task in each full phase. This is not evidence of a universal failure rate. The tuned cases were tested separately before the full rerun; those retries do not replace either full phase.</p>')
 parts.append('<h2>Shared changes</h2><ul><li>Deliver target-client keyboard enter before pointer activation, without assigning global keyboard focus.</li><li>Send whole strings and multi-key sequences in one keyboard transaction; correct F11/F12 key codes.</li><li>Normalize mixed web-document accessibility coordinates, check interface support and summarize blank-text grid cells while preserving reported values.</li><li>Commit numeric values through the Value interface and check that setters actually changed them.</li></ul><p>Known limitation: shortcut-only Ctrl+L navigation still fails in a fresh inactive Chromium diagnostic window. Clicking the address bar first works. This suite does not establish Zen or XWayland reliability. An earlier setup refocus remains recorded in the aborted baseline phase.</p>')
 metrics_path=here/'operation-comparison.json'
 if metrics_path.exists():
  metrics=json.loads(metrics_path.read_text());parts.append('<h2>Recorded operations</h2><table><tr><th>Measure</th><th>Baseline</th><th>Improved</th></tr>')
  for key,label in [('js_calls','JS calls'),('images','Images delivered to the agent'),('tool_errors','Explicit tool errors'),('ax_timeouts','Accessibility scan timeouts')]:parts.append(f'<tr><td>{label}</td><td>{metrics["baseline-v2"][key]}</td><td>{metrics["improved-v1"][key]}</td></tr>')
  parts.append('</table><p>A passing task can still contain failed actions and recovery. Explicit tool errors exclude silent no-ops; the timing review also accounts for identified silent failures. Stronger offline checks agreed with scored passes in 15 office cases per phase, and all five public-page tasks were reviewed against recorded page content.</p>')
 for phase in ['baseline-v2','improved-v1']:
  path=here/'runs'/phase/'timing-breakdown.json'
  if not path.exists():continue
  timing=json.loads(path.read_text())
  if timing['tasks']!=50:continue
  (out/(phase+'-timing.json')).write_text(json.dumps(timing,indent=2))
  labels={'backend_handlers':'Backend handlers','mcp_js_overhead':'MCP/JS overhead','failure_associated_agent_gaps':'Failure-associated agent gaps','other_or_uncertain_agent_gaps':'Other or uncertain agent gaps','startup_teardown_and_unobserved':'Startup, teardown and unobserved overhead'}
  parts.append(f'<h2>{phase} timing</h2><p>{timing["aligned"]}/{timing["tasks"]} task traces aligned. Agent gaps include inference, provider waiting and CLI orchestration. Failure-associated gaps are a reviewed lower-bound estimate; unreviewed silent failures remain in the other/uncertain bucket. <a href="{phase}-timing.json">Per-task accounting and method</a>.</p><table><tr><th>Bucket</th><th>Seconds</th><th>Share</th></tr>')
  for key,label in labels.items():parts.append(f'<tr><td>{label}</td><td>{timing["buckets_s"].get(key,0):.1f}</td><td>{timing["buckets_percent"].get(key,0):.1f}%</td></tr>')
  parts.append('</table>')
 for p in phases:
  rows=p['rows'];attempts=[r for r in rows if r['outcome'] in ['pass','fail']];failed=sum(r['outcome']=='fail' for r in attempts);errors=sum(r['outcome'] not in ['pass','fail'] for r in rows)
  scope='Targeted development checks, excluded from full-suite rates.' if p['phase'].startswith('pilot') else ('Aborted setup attempt; excluded from paired comparison, retained in focus-safety reporting.' if p['phase']=='baseline' else 'Full suite, 50 tasks planned.')
  parts.append(f'<details><summary>{html.escape(p["phase"])}: {len(attempts)-failed} passed, {failed} failed, {errors} setup errors</summary><p>{scope} {len(rows)} tasks recorded. '+(f'Failure rate among evaluated attempts: {failed/len(attempts)*100:.1f}%.' if attempts else '')+f' Provider failures: {sum(r.get("failure_kind")=="provider" for r in rows)}. Refocuses: {sum(bool(r.get("refocus")) for r in rows)}.'+'</p><table><tr><th>Category</th><th>Pass</th><th>Fail</th><th>Setup/harness</th><th>Completed</th></tr>')
  for group in ['native','navigation','web','calc','writer']:
   rr=[r for r in rows if r['group']==group];parts.append(f'<tr><td>{group}</td><td>{sum(r["outcome"]=="pass" for r in rr)}</td><td>{sum(r["outcome"]=="fail" for r in rr)}</td><td>{sum(r["outcome"] not in ["pass","fail"] for r in rr)}</td><td>{len(rr)}/10</td></tr>')
  parts.append('</table><table><tr><th>Task</th><th>Outcome</th><th>Agent time</th><th>Server time</th><th>JS / images / errors</th></tr>')
  for r in rows:parts.append(f'<tr><td>{html.escape(r["id"])}</td><td>{r["outcome"]}</td><td>{r.get("duration_s",0):.1f}s</td><td>{r["tool_s"]:.1f}s</td><td>{r["js_calls"]} / {r["images"]} / {len(r["tool_errors"])}</td></tr>')
  parts.append('</table>')
  for r in rows:
   if r['outcome']!='pass' or r['tool_errors']:
    parts.append('<details><summary>'+html.escape(r['id'])+' evidence</summary><p>'+html.escape(r['prompt'])+'</p><p>'+html.escape(r.get('error',r['final']))+'</p><pre>'+html.escape(json.dumps({'grade':r.get('grade'),'tool_errors':r['tool_errors']},indent=2))+'</pre></details>')
  parts.append('</details>')
 parts.append('<p>Server time is measured handler elapsed time. The remainder includes model inference, provider waiting, CLI startup and orchestration. Tool errors can occur in successful tasks. Success checks do not prove every requested intermediate action. Source hashes, focus logs, prompts and full raw traces remain in the repository.</p></body></html>')
 temp=out/'index.tmp';temp.write_text(''.join(parts));temp.replace(out/'index.html')
 print(json.dumps({p['phase']:len(p['rows']) for p in phases}),flush=True)
if '--watch' in sys.argv:
 while True:
  try:subprocess.run([sys.executable,__file__],check=True)
  except Exception as ex:print(str(ex),flush=True)
  time.sleep(15)
else:build()
