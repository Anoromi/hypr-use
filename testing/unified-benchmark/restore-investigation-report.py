"""Publish clean-run evidence and timing without exposing private session messages."""
import collections,html,json,shutil,statistics,subprocess
from pathlib import Path
b=Path(__file__).resolve().parent
out=Path('/home/anoromi/Artifacts/hypr-use-restore-comparison')
phases=[f'astra-restore-clean-{n}' for n in range(1,4)]+[f'astra-restore-ax-fix-{n}' for n in range(1,4)]
subprocess.run(['python3',str(b/'audit-clean-context.py'),*phases],check=True)
rows=[]
for phase in phases:
 p=b/phase;d=p/'restore-last-tab';fixed='ax-fix' in phase
 if fixed:
  events=[json.loads(l)['event'] for l in (d/'events.jsonl').read_text().splitlines()]
  calls=[e['item'] for e in events if e['type']=='item.started' and e.get('item',{}).get('type')=='mcp_tool_call']
  assert len(calls)==2, 'Review nontrivial fixed run before classifying timing'
  (d/'timing-annotations.json').write_text(json.dumps({'gap_before_call':{c['id']:'normal' for c in calls},'after_last_call':'normal','rationale':'Reviewed initial two-tab AX state, one restore shortcut, resulting three-tab state and correct success report. No recovery turns.'},indent=2))
 subprocess.run(['python3',str(b/'short-breakdown.py'),phase],stdout=subprocess.DEVNULL,check=True)
 timing=json.loads((p/'breakdown.json').read_text());audit=json.loads((p/'context-audit.json').read_text())
 first=json.loads((d/'wire.jsonl').read_text().splitlines()[0]);texts=[c['text'] for c in first['response']['result']['content'] if c['type']=='text']
 tab_lines=[l.strip() for t in texts for l in t.splitlines() if ' page tab ' in l and ' page tab list ' not in l and 'y: 0,' in l]
 setup=json.loads((p/'owned-browser.json').read_text());assert f"@pid={setup['pid']}@" in texts[0]
 assert len(tab_lines)==(2 if fixed else 3)
 assert not any(m['target_name_present'] or m['previous_result_terms_present'] for m in audit['messages'])
 assert all(json.loads((p/'source-verification.json').read_text()).values())
 row={'phase':phase,'fixed':fixed,'seconds':timing['total_s'],'initial_ax_tabs':tab_lines,'initial_cdp_tabs':audit['initial_tabs'],'final_agent_message':(d/'final.txt').read_text(),'timing':timing,'audit':audit,'cleanup':json.loads((p/'cleanup.json').read_text())}
 rows.append(row)
 dest=out/phase;dest.mkdir(exist_ok=True)
 for name in ['context-audit.json','breakdown.json','manifest.json','source-verification.json','tabs-start.json','tabs-final.json','cleanup.json']:
  shutil.copy2(p/name,dest/name)
 (dest/'final.txt').write_text(row['final_agent_message'])
for fixed in [False,True]:
 subset=[r for r in rows if r['fixed']==fixed];print('fixed',fixed,'median',statistics.median(r['seconds'] for r in subset))
(out/'investigation.json').write_text(json.dumps(rows,indent=2))
old=out/'index.html'
if old.exists() and not (out/'preflight-warmed.html').exists():
 previous=old.read_text();previous=previous.replace('<body>','<body><p><strong>Superseded preflight-warmed result. Causal claims below were not established by this run. See <a href="./">clean-run investigation</a>.</strong></p>',1)
 (out/'preflight-warmed.html').write_text(previous)
parts=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Restore-tab investigation</title><style>body{font:16px system-ui;line-height:1.55;max-width:1050px;margin:40px auto;padding:0 20px;color:#222}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{text-align:left;padding:8px;border-bottom:1px solid #ddd}a{color:#1659a5}pre{white-space:pre-wrap}h1{font-size:28px}h2{font-size:21px}details{margin:18px 0}</style><body><h1>Restore-tab investigation</h1><p>Six fresh GPT-6 Astra xhigh runs, separate browser profiles, separate agent threads, empty working directories except the brief AGENTS instruction, and no restore preflight. All ran on the same desktop in workspace 902 without refocusing the user.</p>',
'<h2>What was wrong</h2><p>No previous-result terms or closed-tab name appeared in the recorded starting messages. Actual calls used only discovery and the JS MCP. The initial AX tree was stale: CDP reported two tabs, while AX reported three. All three agents restored the tab but then failed to recognize success because the tab count appeared unchanged. Target PID was checked against each owned browser.</p>',
'<p>In two separate diagnostic profiles, an AX-only observation retained the closed tab. Repeated AX reads in the second profile did not fix it. Screenshot preparation woke background Wayland frames and the next tree showed the correct two tabs, with CDP remaining unchanged. The plugin already performs this wake-up before screenshots and input. AX-only observation had skipped it.</p>',
'<p>The fix adds the existing native prepare operation before AX-only scans, followed by the same 120 ms settling interval used for screenshots. No screenshot is captured or sent. Native lock and privacy checks remain in effect. Five existing adapter tests and three AX preparation regression tests passed; the fresh live runs below check actual state, target identity and foreground focus. The fixed delay is not a guarantee that every application has finished updating.</p>',
'<h2>Clean runs</h2><table><tr><th>Run</th><th>Total</th><th>JS calls</th><th>Images</th><th>Result</th></tr>']
for r in rows:
 t=r['timing']['tasks'][0]
 parts.append(f'<tr><td>{html.escape(r["phase"])}</td><td>{r["seconds"]:.2f} s</td><td>{t["js_calls"]}</td><td>{t["screenshots"]}</td><td>Tab restored; '+('correct success report' if r['fixed'] else 'agent could not confirm')+'</td></tr>')
parts.append('</table>')
oldmedian=statistics.median(r['seconds'] for r in rows if not r['fixed']);newmedian=statistics.median(r['seconds'] for r in rows if r['fixed']);reference=42.654840003
parts.append(f'<p>Median before: {oldmedian:.2f} s. Median after: {newmedian:.2f} s, {100*(1-newmedian/oldmedian):.1f}% less elapsed time. Three repetitions per condition establish repeatability here, not a broad performance claim.</p>')
parts.append(f'<p>The <a href="https://huggingface.co/datasets/anonymousmypcbench/cua-speedrun-trajectories">published third-party trajectory</a> took {reference:.2f} s for the same <a href="https://github.com/xlang-ai/OSWorld/blob/main/evaluation_examples/examples/chrome/06fe7178-4491-4589-810f-2e2bc9502122.json">OSWorld restore-tab task</a>. Our new median is {100*(1-newmedian/reference):.1f}% less elapsed time. This is not an OpenAI-native-app benchmark: host, automation stack and startup/recovery behavior differ. The published run includes its own failed startup attempts. Browser preparation and grading are outside our timer; our timer includes the fresh Codex process lifecycle.</p>')
parts.append('<h2>Where time went</h2><p>Percentages below use total elapsed time across the three runs in each condition. Model-turn gaps include inference, provider waiting and orchestration; they are not pure inference time. Recovery is classified separately because it follows perceived failure caused by the stale initial observation.</p><table><tr><th>Bucket</th><th>Before</th><th>After</th></tr>')
aggregates=[]
for fixed in [False,True]:
 subset=[r for r in rows if r['fixed']==fixed];total=sum(r['seconds'] for r in subset);c=collections.Counter()
 for r in subset:
  for k,v in r['timing']['aggregate'].items():c[k]+=v['seconds']
 aggregates.append((c,total))
for k in dict.fromkeys([*aggregates[0][0],*aggregates[1][0]]):
 parts.append('<tr><td>'+html.escape(k)+'</td>'+''.join(f'<td>{c[k]/3:.2f} s/run · {100*c[k]/total:.1f}%</td>' for c,total in aggregates)+'</tr>')
parts.append('</table><h2>Evidence and corrections</h2><p>The earlier 22.30-second run restored and reclosed the tab before timing, which also woke background frames. It is a warmed diagnostic result and was insufficient evidence for the claimed fix. The original 141.62-second run did not validate committed navigation; early closure was a possible additional setup problem, not a proven sole cause. Neither run enters the clean medians above. Shared OS caches and provider prompt caching were not disabled.</p>')
for r in rows:
 phase=r['phase'];parts.append(f'<details><summary>{phase}</summary><p>Thread {r["audit"]["thread_id"]}</p><p>{html.escape(r["final_agent_message"])}</p><p><a href="{phase}/context-audit.json">Context audit</a> · <a href="{phase}/breakdown.json">Timing</a> · <a href="{phase}/manifest.json">Manifest</a> · <a href="{phase}/source-verification.json">Source checks</a> · <a href="{phase}/tabs-start.json">Initial tabs</a> · <a href="{phase}/tabs-final.json">Final tabs</a> · <a href="{phase}/cleanup.json">Cleanup</a></p><pre>{html.escape(chr(10).join(r["initial_ax_tabs"]))}</pre></details>')
parts.append('<p><a href="investigation.json">Full measured evidence</a> · <a href="preflight-warmed.html">Superseded warmed report</a> · <a href="invalid-setup.html">Unvalidated original setup</a></p></body></html>')
old.write_text(''.join(parts))
