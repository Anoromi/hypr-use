"""Publish timing metadata only; never export private rollout reasoning."""
import json, pathlib, datetime, statistics, collections, csv, html
root=pathlib.Path(__file__).resolve().parent
source=next(pathlib.Path('/home/anoromi/.codex/sessions/2026/09/07').glob('*01a07c2d-6414-7061-bb86-1426fc003f31*'))
rows=[json.loads(l) for l in source.open()]
def ts(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def union(intervals):
 out=[]
 for a,b in sorted(intervals):
  if out and a<=out[-1][1]:out[-1][1]=max(b,out[-1][1])
  else:out.append([a,b])
 return sum(b-a for a,b in out)
def fmt(s):return f'{int(s//60)}m {s%60:04.1f}s'
turns=[];items=[];usage={}
for r in rows:
 p=r.get('payload',{})
 if r['type']=='token_usage_record':usage[p['response_id']]=p['usage']
 if r['type']!='event_msg':continue
 if p.get('type')=='task_started':turns.append({'start':ts(r['timestamp'])})
 if p.get('type') in ('task_complete','turn_aborted'):turns[-1]['end']=ts(r['timestamp'])
 if p.get('type')=='item_completed':
  it=p['item'];items.append({'type':it['type'],'start':p['started_at_ms']/1000,'end':p['completed_at_ms']/1000,'item':it})
calls=[]
replay=json.load(open('/home/anoromi/Artifacts/hypr-use-calc-test/data.json'))['steps']
replaytools=[(i+1,x) for i,x in enumerate(replay) if x['kind']=='tool']
for x in items:
 if x['type']!='McpToolCall':continue
 i=len(calls)+1;it=x['item'];duration=it['duration'];n,t=next((j,t) for j,t in enumerate(turns,1) if t['start']<=x['start']<=t['end'])
 step,record=replaytools[i-1];assert record['tool']==it['tool'] and record['args']==it['arguments']
 prev=calls[-1]['end'] if calls and calls[-1]['turn']==n else t['start']
 calls.append(dict(number=i,replay_step=step,turn=n,tool=it['tool'],status=it['status'],args=it['arguments'],start=x['start'],end=x['end'],seconds=duration['secs']+duration['nanos']/1e9,wall_seconds=x['end']-x['start'],gap_before_seconds=max(0,x['start']-prev)))
assert len(calls)==94
active=sum(t['end']-t['start'] for t in turns);elapsed=turns[-1]['end']-turns[0]['start'];toolwall=union((c['start'],c['end']) for c in calls);compact=union((x['start'],x['end']) for x in items if x['type']=='ContextCompaction')
summary={'elapsed_seconds':elapsed,'active_seconds':active,'pause_seconds':elapsed-active,'tool_wall_seconds':toolwall,'tool_execution_seconds':sum(c['seconds'] for c in calls),'compaction_seconds':compact,'agent_and_client_other_seconds':active-toolwall-compact,'calls':len(calls),'failed_calls':sum(c['status']=='failed' for c in calls),'median_tool_seconds':statistics.median(c['seconds'] for c in calls),'usage_records':len(usage),'usage':{k:sum(u.get(k,0) for u in usage.values()) for k in next(iter(usage.values()))}}
groups=[]
for name in sorted(set(c['tool'] for c in calls)):
 cs=[c for c in calls if c['tool']==name];groups.append({'tool':name,'count':len(cs),'failed':sum(c['status']=='failed' for c in cs),'total':sum(c['seconds'] for c in cs),'median':statistics.median(c['seconds'] for c in cs),'maximum':max(c['seconds'] for c in cs)})
phases=[]
for a,b,name in [(1,2,'Initial launch denied'),(3,12,'Launch, welcome dialog, approval blocks'),(13,15,'Resume and close welcome'),(16,40,'Open CSV: file-picker retries'),(41,53,'CSV import, including context compaction'),(54,61,'Dismiss tip, format header, inspect last row'),(62,73,'Save As, then keyboard-grab block'),(74,89,'Resume, correct format and filename, save ODS'),(90,94,'Final GUI checks')]:
 cs=calls[a-1:b];t=turns[cs[0]['turn']-1];start=calls[a-2]['end'] if a>1 and calls[a-2]['turn']==cs[0]['turn'] else t['start'];phases.append({'phase':name,'calls':f'{a}–{b}','seconds':cs[-1]['end']-start,'tool_seconds':sum(c['seconds'] for c in cs)})
result={'summary':summary,'turns':turns,'phases':phases,'by_tool':groups,'calls':calls}
(root/'calc-session/timing.json').write_text(json.dumps(result,indent=2))
out=pathlib.Path('/home/anoromi/Artifacts/hypr-use-calc-timing');out.mkdir(exist_ok=True)
(out/'timing.json').write_text(json.dumps(result,indent=2))
with (out/'steps.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['call','replay_step','turn','tool','status','start_UTC','execution_seconds','wall_seconds','gap_before_seconds','arguments'])
 for c in calls:w.writerow([c['number'],c['replay_step'],c['turn'],c['tool'],c['status'],datetime.datetime.fromtimestamp(c['start'],datetime.timezone.utc).isoformat(),c['seconds'],c['wall_seconds'],c['gap_before_seconds'],json.dumps(c['args'])])
def table(headers,records):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in records)+'</tbody></table></div>'
parts=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calc test timing</title><link rel="stylesheet" href="styles.css"><main><h1>Calc test timing</h1><p>7 September 2026 · 23:02:24 to 23:41:31 JST · gpt-5.6-sol, high reasoning effort</p><p><a href="../hypr-use-calc-test/">Recorded thread and screenshots</a> · <a href="steps.csv">Every call as CSV</a> · <a href="timing.json">Timing data</a></p>']
parts+=['<h2>Where the time went</h2>',table(['Category','Time','Share of elapsed'],[(n,fmt(v),f'{100*v/elapsed:.1f}%') for n,v in [('Portal calls, wall time',toolwall),('Context compaction',compact),('Other active agent and client time',active-toolwall-compact),('Between-run pauses',elapsed-active),('Total',elapsed)]]),'<p>Active runs took '+fmt(active)+'. Between-run pauses include discussion, implementation, and server restarts. This measures the desktop thread; earlier research and later independent workbook validation are outside this window.</p>']
parts+=['<h2>What was slow</h2><ul><li>The file picker needed 25 calls. Three long path entries took about 68 seconds of tool execution alone, then the agent navigated using short entries. This was the largest avoidable interaction sequence.</li><li>Permission configuration interrupted three attempts. The largest pause was 11m 02s while we discussed and implemented full mode. That is operator and development time, not portal latency.</li><li>Context compaction stopped progress for 106.8 seconds. Repeated screenshots and accessibility snapshots are plausible contributors to context growth; the log does not establish their individual contribution.</li><li>Keyboard typing dispatches one portal keyboard operation per character, plus a 15ms sleep. The 23.6-second path entry cannot be explained by that sleep alone. Every character also incurs the keyboard call overhead.</li><li>Successful clicks and key presses often take several seconds. Source code collects post-action state, and some paths collect pre-action state too. There are no nested spans to separate screenshot, accessibility, IPC, and application time.</li><li>Sixteen calls report failure, including calls whose action closed the target successfully. Failed calls understate wasted work: malformed typing and wrong-field input can return success.</li></ul>']
parts+=['<h2>Task phases</h2><p>Each phase starts at the previous call completion, or at turn start after a restart. It includes the gap before its first call. End-of-turn reporting time is excluded from phases but included in totals.</p>',table(['Phase','Calls','Elapsed','Tool execution'],[(p['phase'],p['calls'],fmt(p['seconds']),fmt(p['tool_seconds'])) for p in phases])]
parts+=['<h2>By tool</h2>',table(['Tool','Calls','Failed','Total execution','Median','Slowest'],[(g['tool'],g['count'],g['failed'],fmt(g['total']),f"{g['median']:.2f}s",f"{g['maximum']:.2f}s") for g in sorted(groups,key=lambda g:-g['total'])])]
parts+=['<h2>What to change first</h2><ol><li>Make file-picker text entry reliable. Add explicit focused-field targeting or an owner-configured insertion method, then batch key delivery in the plugin. Verify the entered path before opening it.</li><li>Configure permissions before launching the agent. Return a clear policy error and stop retrying equivalent actions when a global block is active.</li><li>Avoid full snapshots after every character or action in a known sequence. Capture at checkpoints, and return only the required image and accessibility fields.</li><li>Add timing spans inside the server for target resolution, policy, input dispatch, screenshot, accessibility, serialization, and response size. This run cannot tell whether a Python-to-Go rewrite would help.</li><li>Once tool behavior is reliable, compare lower reasoning effort on the same task. The current residual includes model wait, generation, transport, and client overhead, so it is not a direct model inference measurement.</li></ol>']
parts+=['<h2>Every tool call</h2><p>Execution is the recorded MCP duration. Gap is time since the previous tool completed within the same run; it may include model work, messages, orchestration, or compaction. Replay step numbers match the existing viewer.</p><label>Filter calls <input id="filter" type="search" placeholder="Tool, status, or argument"></label><p id="count"></p><div id="calls">',table(['Call','Replay step','Run','Start JST','Tool / arguments','Status','Execution','Gap before'],[(c['number'],c['replay_step'],c['turn'],datetime.datetime.fromtimestamp(c['start'],datetime.timezone(datetime.timedelta(hours=9))).strftime('%H:%M:%S'),c['tool']+' '+json.dumps({k:v for k,v in c['args'].items() if k!='app'},ensure_ascii=False),c['status'],f"{c['seconds']:.3f}s",f"{c['gap_before_seconds']:.3f}s") for c in calls]),'</div>']
parts+=['<h2>Measurement limits</h2><p>All 94 calls were matched by tool name and arguments against the public replay. Start/end times come from Codex item events; execution durations come from the MCP item. The difference includes client overhead. Unioned wall intervals avoid double counting concurrent calls. Token records cover '+str(len(usage))+' responses, with '+format(summary['usage'].get('input_tokens',0),',')+' input tokens and '+format(summary['usage'].get('output_tokens',0),',')+' output tokens summed across requests. Repeated input is counted again; this is not unique context size. Private reasoning content is not exported.</p></main><script src="script.js"></script></html>']
(out/'index.html').write_text('\n'.join(parts))
(out/'styles.css').write_text('body{font-family:system-ui,sans-serif;background:#fafafa;color:#222;margin:0}main{max-width:1200px;margin:auto;padding:28px}h1{font-size:26px}h2{font-size:20px;margin-top:32px}p,li{line-height:1.6;max-width:1000px}li{margin:8px 0}a{color:#574329}table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}th,td{text-align:left;border-bottom:1px solid #ddd;padding:10px;vertical-align:top}th{background:#eee}td:nth-last-child(-n+2){white-space:nowrap}.scroll{overflow:auto}input{padding:8px;border:1px solid #999;border-radius:4px;font:inherit}#calls td:nth-child(5){min-width:280px;overflow-wrap:anywhere}tr[hidden]{display:none}')
(out/'script.js').write_text("const rows=[...document.querySelectorAll('#calls tbody tr')];const filter=document.querySelector('#filter');function update(){let n=0;for(const row of rows){row.hidden=!row.textContent.toLowerCase().includes(filter.value.toLowerCase());if(!row.hidden)n++;}document.querySelector('#count').textContent=n+' of '+rows.length+' calls';}filter.addEventListener('input',update);update();")
print(json.dumps({'summary':summary,'phases':phases,'groups':groups},indent=2))
