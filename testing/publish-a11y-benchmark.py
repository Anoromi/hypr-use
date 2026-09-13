"""Publish the recorded accessibility-enabled Calc run and internal timings."""
import base64,collections,html,json,shutil
from pathlib import Path
r=Path(__file__).resolve().parent
session=r/'calc-session-a11y-20260909'
out=Path('/home/anoromi/Artifacts/hypr-use-calc-a11y');out.mkdir(exist_ok=True)
def readlines(p):
 if not p.exists():return []
 rows=[]
 for line in p.read_text().splitlines():
  try:rows.append(json.loads(line))
  except ValueError:pass
 return rows
wire=readlines(session/'wire.jsonl');thread=readlines(session/'thread.jsonl');calls=[]
for index,row in enumerate(wire,1):
 req=row.get('request',{});res=row.get('response') or {};result=res.get('result') or {};timing=result.get('_meta',{}).get('hypr-use/timing',{})
 images=[];texts=[]
 for c in result.get('content',[]):
  if c.get('type')=='text':texts.append(c.get('text',''))
  if c.get('type')=='image':
   try:data=base64.b64decode(c['data'],validate=True)
   except (ValueError,KeyError):continue
   name=f'call-{index}-{len(images)+1}.png';(out/name).write_bytes(data);images.append(name)
 calls.append({'number':index,'time':row.get('time'),'tool':req.get('params',{}).get('name'),'args':req.get('params',{}).get('arguments'),'failed':result.get('isError',False),'duration_ms':row.get('duration_ms',timing.get('total_ms',0)),'timing':timing,'images':images,'text':'\n'.join(texts)})
messages=[x['item'].get('text','') for x in thread if x.get('type')=='item.completed' and x.get('item',{}).get('type')=='agent_message']
finished=(session/'exit.json').exists();verification=json.loads((session/'workbook-verification.json').read_text()) if (session/'workbook-verification.json').exists() else None
summary={'calls':len(calls),'failed_calls':sum(c['failed'] for c in calls),'tool_seconds':sum(c['duration_ms'] for c in calls)/1000,'finished':finished,'verification':verification}
for name in ['run.json','exit.json','metrics.json']:
 if (session/name).exists():summary[name]=json.loads((session/name).read_text())
(out/'data.json').write_text(json.dumps({'summary':summary,'calls':calls,'messages':messages}))
for name in ['thread.jsonl','wire.jsonl','workbook-verification.json','metrics.json','run.json','exit.json','FINDINGS.md','interventions.jsonl','verification-status.json']:
 if (session/name).exists():shutil.copyfile(session/name,out/name)
for f in session.glob('*.ods'):shutil.copyfile(f,out/f.name)
for name in ['usa-age-groups-1950-2026.csv','SOURCE.md']:
 shutil.copyfile(r/'calc-data'/name,out/name)
(out/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calc benchmark with accessibility</title><link rel="stylesheet" href="styles.css"><main><h1>Calc benchmark with accessibility</h1><p>Codex subagent · LibreOffice · USA age groups, 1950–2026</p><p id="summary"></p><nav><a href="FINDINGS.md">Outcome and failures</a> · <a href="interventions.jsonl">Supervisor intervention</a> · <a href="thread.jsonl">Recorded thread</a> · <a href="wire.jsonl">Raw tool responses</a> · <a href="data.json">Timing data</a> · <a href="SOURCE.md">Data sources</a></nav><div id="downloads"></div><h2>Agent updates</h2><div id="messages"></div><h2>Tool calls</h2><label>Call <select id="select"></select></label><p id="call"></p><details><summary>Arguments</summary><pre id="args"></pre></details><h3>Internal timings</h3><p>Inclusive times include child spans. Exclusive times exclude children; add exclusive times and unattributed time to reconcile against the server total.</p><div class="scroll"><table><thead><tr><th>Stage</th><th>Inclusive ms</th><th>Exclusive ms</th></tr></thead><tbody id="timings"></tbody></table></div><details><summary>Tool text</summary><pre id="text"></pre></details><div id="images"></div></main><script src="script.js"></script></html>''')
(out/'styles.css').write_text('body{background:#fafafa;color:#222;font:15px/1.5 system-ui;margin:0}main{max-width:1160px;margin:auto;padding:24px}h1{font-size:26px}h2{font-size:20px;margin-top:28px}a{color:#574329}select{padding:8px;font:inherit;max-width:100%}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{border-bottom:1px solid #ddd;text-align:left;padding:8px}.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:400px;overflow:auto}img{max-width:100%;height:auto;border:1px solid #ccc;margin-top:16px}#messages p{border-bottom:1px solid #ddd;padding-bottom:12px}')
(out/'script.js').write_text('''const q=id=>document.getElementById(id);fetch('data.json').then(r=>r.json()).then(d=>{const s=d.summary;q('summary').textContent=`${s.finished?'Run ended':'Run in progress'} · ${s.calls} calls · ${s.failed_calls} errors · ${(s.tool_seconds/60).toFixed(1)} minutes in tools. ${s.verification?'Workbook independently verified.':s.finished?'No verified output workbook.':''}`;if(s.verification){const a=document.createElement('a');a.href=s.verification.file.split('/').pop();a.textContent='Download verified spreadsheet';q('downloads').append(a);}for(const text of d.messages){const p=document.createElement('p');p.textContent=text;q('messages').append(p);}d.calls.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${c.number}. ${c.tool} · ${(c.duration_ms/1000).toFixed(2)}s${c.failed?' · error':''}`;q('select').append(o);});function render(){const c=d.calls[Number(q('select').value)];if(!c)return;q('call').textContent=`${c.tool} · ${(c.duration_ms/1000).toFixed(3)} seconds`;q('args').textContent=JSON.stringify(c.args,null,2);q('text').textContent=c.text;q('timings').replaceChildren();for(const span of c.timing.spans||[]){const tr=document.createElement('tr');let depth=0,parent=span.parent;while(parent!==null&&parent!==undefined){depth++;parent=c.timing.spans[parent].parent;}for(const v of ['  '.repeat(depth)+span.stage,span.duration_ms.toFixed(2),span.self_ms.toFixed(2)]){const td=document.createElement('td');td.textContent=v;td.style.whiteSpace='pre';tr.append(td);}q('timings').append(tr);}q('images').replaceChildren();for(const src of c.images){const img=document.createElement('img');img.src=src;img.alt='Server screenshot for call '+c.number;q('images').append(img);}}q('select').onchange=render;if(d.calls.length){q('select').value=d.calls.length-1;render();}});''')
print(json.dumps(summary))
