import json,subprocess,time,sys
from pathlib import Path
r=Path(__file__).resolve().parent
run=json.loads((r/'calc-session/run.json').read_text())
thread=next(json.loads(l)['thread_id'] for l in (r/'calc-session/thread.jsonl').read_text().splitlines() if json.loads(l).get('type')=='thread.started')
original=run['command'];flags=[]
for i,arg in enumerate(original):
 if arg=='-c':flags+=['-c',original[i+1]]
for tool in ('get_app_state','click','press_key','type_text'):
 flags+=['-c',f'mcp_servers.hypr_calc.tools.{tool}.output_token_limit=100000']
args=['codex','exec','resume','--json',*flags,thread,'-']
path=r/'calc-session/exit.json'
if path.exists():path.unlink()
prompt=sys.argv[1] if len(sys.argv)>1 else 'The test operator corrected the server launch permission for the user-authorized LibreOffice launch. The server now accepts only launch_app app=libreoffice and confines subsequent actions to LibreOffice. No clipboard or foreground fallback is authorized. Retry exactly launch_app app=libreoffice, then complete the original task. The CSV now exists and has been validated: 77 rows, 12 columns; 1950-2023 Estimates, 2024-2026 Medium projection. Keep all errors and retries visible in your final report.'
with (r/'calc-session/interventions.jsonl').open('a') as f:f.write(json.dumps({'time':time.time(),'prompt':prompt})+'\n')
with (r/'calc-session/thread.jsonl').open('a') as out,(r/'calc-session/thread.stderr').open('a') as err:
 x=subprocess.run(args,input=prompt,text=True,stdout=out,stderr=err,cwd=r.parent)
path.write_text(json.dumps({'finished':time.time(),'exit_code':x.returncode}))
