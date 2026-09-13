import base64,html,json,shutil
from pathlib import Path
r=Path(__file__).resolve().parent
out=Path('/home/anoromi/Artifacts/hypr-use-calc-test');out.mkdir(parents=True,exist_ok=True)
steps=[];thread=None
for line in (r/'calc-session/thread.jsonl').read_text().splitlines():
    try:x=json.loads(line)
    except json.JSONDecodeError:continue
    if x.get('type')=='thread.started':thread=x.get('thread_id')
    if x.get('type')!='item.completed':continue
    i=x.get('item',{});kind=i.get('type')
    if kind=='agent_message':steps.append({'kind':'message','text':i.get('text',''),'images':[]});continue
    if kind!='mcp_tool_call':continue
    result=i.get('result') or {};texts=[];images=[]
    def consume(content, depth=0):
        for c in content:
            if c.get('type')=='text':
                value=c.get('text','')
                try:nested=json.loads(value)
                except (ValueError,TypeError):nested=None
                if depth<4 and isinstance(nested,dict) and isinstance(nested.get('content'),list):
                    texts.append('[Tool returned nested JSON content; decoded for replay.]')
                    consume(nested['content'],depth+1)
                else:texts.append(value)
            if c.get('type')=='image':
                try:raw=base64.b64decode(c['data'],validate=True)
                except ValueError:
                    texts.append('[Screenshot was serialized into text and truncated; no usable image remained in this response.]')
                    continue
                name=f'step-{len(steps)+1}-{len(images)+1}.png';(out/name).write_bytes(raw);images.append(name)
    consume(result.get('content',[]))
    steps.append({'kind':'tool','tool':i.get('tool'),'args':i.get('arguments'),'status':i.get('status'),'error':i.get('error'),'text':'\n\n'.join(texts),'images':images})
interventions=[json.loads(l) for l in (r/'calc-session/interventions.jsonl').read_text().splitlines()] if (r/'calc-session/interventions.jsonl').exists() else []
meta={'thread':thread,'steps':steps,'interventions':interventions,'prompt':(r/'calc-prompt.txt').read_text(),'finished':(r/'calc-session/exit.json').exists()}
(out/'data.json').write_text(json.dumps(meta))
shutil.copyfile(r/'calc-session/thread.jsonl',out/'thread.jsonl')
for name in ['usa-age-groups-1950-2026.csv','usa-age-groups-1950-2026.ods','SOURCE.md','metadata.json']:
    if (r/'calc-data'/name).exists():shutil.copyfile(r/'calc-data'/name,out/name)
(out/'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calc computer-use recording</title><style>
body{margin:0;background:#fafafa;color:#0f172a;font:15px/1.5 system-ui}main{max-width:1160px;margin:auto;padding:24px}h1{font-size:25px;margin:0 0 8px}h2{font-size:18px}a{color:#2563eb}nav{display:flex;gap:16px;flex-wrap:wrap;margin:16px 0}button,select{font:inherit;background:white;border:1px solid #cbd5e1;border-radius:4px;padding:8px}button{cursor:pointer}button:disabled{opacity:.4}select{flex:1;min-width:180px}article{border-top:1px solid #cbd5e1;padding-top:16px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;border:1px solid #e2e8f0;padding:12px;max-height:360px;overflow:auto;font:13px/1.5 monospace}img{display:block;max-width:100%;height:auto;margin:16px auto;border:1px solid #cbd5e1}summary{cursor:pointer;padding:8px 0}.error{color:#b91c1c}#controls{display:flex;gap:8px;margin:20px 0}#status{color:#475569}#findings{border-left:3px solid #94a3b8;padding-left:16px}p{max-width:900px}
</style><main><h1>Calc computer-use recording</h1><p>USA population by age group, 1950–2026. A Codex agent operates LibreOffice through the Hyprland portal on workspace 2.</p><p id="status">Loading recording…</p><div id="findings"></div><nav><a href="findings.md">Failure analysis</a><a href="wire.jsonl" download>Raw server responses, final resume</a><a href="final-server-screenshot.png">Full final screenshot</a><a href="thread.jsonl" download>Raw thread JSONL</a><a href="usa-age-groups-1950-2026.csv" download>Source CSV</a><a href="usa-age-groups-1950-2026.ods" id="workbook" hidden download>Spreadsheet</a><a href="SOURCE.md">Data sources and methodology</a></nav><p>The CSV was researched and prepared separately. The desktop agent imports and saves through Calc. Launches are pinned to workspace 2 by the test server. Clipboard is disabled. This records visible messages and tool results, not private model reasoning.</p><details><summary>Task instructions</summary><pre id="prompt"></pre></details><details><summary>Operator interventions</summary><pre id="interventions"></pre></details><div id="controls"><button id="prev">Previous</button><select id="steps" aria-label="Recorded step"></select><button id="next">Next</button></div><article><h2 id="title"></h2><pre id="args" hidden></pre><details open><summary>Response</summary><pre id="response"></pre></details><div id="images"></div></article></main><script>
let data,at=0;const q=id=>document.getElementById(id);function render(){const s=data.steps[at];if(!s)return;q('steps').value=at;q('title').textContent=`${at+1}. ${s.kind==='message'?'Agent message':s.tool}`;q('title').className=s.status==='failed'?'error':'';q('args').hidden=s.kind==='message';q('args').textContent=JSON.stringify(s.args,null,2);q('response').textContent=s.text+(s.error?'\\n'+JSON.stringify(s.error):'');q('images').replaceChildren(...s.images.map(src=>{const a=document.createElement('a');a.href=src;a.target='_blank';const im=document.createElement('img');im.src=src;im.alt=`Screenshot returned at step ${at+1}`;a.append(im);return a}));q('prev').disabled=at===0;q('next').disabled=at===data.steps.length-1;}fetch('data.json').then(r=>r.json()).then(d=>{data=d;q('status').textContent=`${d.finished?'Run finished':'Run in progress'} · ${d.steps.filter(s=>s.kind==='tool').length} completed tool calls · ${d.steps.filter(s=>s.status==='failed').length} failed calls · Thread ${d.thread}`;q('prompt').textContent=d.prompt;q('interventions').textContent=d.interventions.map(x=>new Date(x.time*1000).toISOString()+'\\n'+x.prompt).join('\\n\\n')||'None';d.steps.forEach((s,n)=>{let o=document.createElement('option');o.value=n;o.textContent=`${n+1}. ${s.kind==='message'?'Agent message':s.tool}${s.status==='failed'?' — failed':''}`;q('steps').append(o)});at=Math.max(0,d.steps.length-1);render()});q('prev').onclick=()=>{at--;render()};q('next').onclick=()=>{at++;render()};q('steps').onchange=e=>{at=Number(e.target.value);render()};fetch('findings.txt').then(r=>r.ok?r.text():'').then(t=>{q('findings').textContent=t});fetch('usa-age-groups-1950-2026.ods',{method:'HEAD'}).then(r=>{q('workbook').hidden=!r.ok});
</script></html>''')
print('Published',len(steps),'steps')
