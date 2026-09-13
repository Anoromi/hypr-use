import os,sys,json,subprocess,threading,time,signal
from pathlib import Path
from monitor import Monitor,ctl
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent
phase=sys.argv[1] if len(sys.argv)>1 else 'baseline';selected=set(sys.argv[2:]);out=here/phase;out.mkdir(exist_ok=True)
tasks=json.loads(Path(os.environ.get('HYPR_USE_TASK_FILE',str(here/'tasks.json'))).read_text());tasks=[t for t in tasks if not selected or t['id'] in selected]
effort=os.environ.get('HYPR_USE_REASONING_EFFORT','high')
target_classes={t['app'] for t in tasks}
if any(c.startswith('libreoffice-') for c in target_classes):target_classes.update(['libreoffice-calc','libreoffice-writer','libreoffice-startcenter','soffice'])
monitor=Monitor(out/'focus.jsonl',sorted(target_classes))
current=None

def halt():
 if current and current.poll() is None:
  try:os.killpg(current.pid,signal.SIGTERM)
  except ProcessLookupError:pass
monitor.callback=halt
results=[]
for task in tasks:
 if monitor.trigger.is_set():break
 monitor.stage=task['id'];d=out/task['id'];d.mkdir(exist_ok=True)
 e=os.environ.copy();e.update(HYPR_AGENT_PORTAL_PERMISSION_MODE='full',HYPR_AGENT_PORTAL_APPROVAL_POLICY='never',HYPR_AGENT_PORTAL_CONFINE=('class:'+task['app']+',class:soffice,class:libreoffice-startcenter' if task['app'].startswith('libreoffice-') else 'class:'+task['app']),HYPR_USE_WIRE_LOG=str(d/'wire.jsonl'),HYPR_USE_PORTAL_LOG=str(d/'portal.jsonl'))
 prompt=f'''Use only the cua_repl MCP server to perform this GUI task on this machine. Do not use shell, web tools, filesystem APIs or subagents. The target is the background app class {task['app']}. Keep the user's foreground window unchanged. Use cua.getApp('{task['app']}') or select an exact window id from cua.listApps() if there are dialogs. Use the provided JS API; observations emit themselves. Prefer AX indices, but use screenshots and coordinates if needed. Stop after at most 12 js calls or if blocked. Do not fabricate success. Report the final observed outcome concisely. Task: {task['prompt']}'''
 if os.environ.get('HYPR_USE_TASK_CONTEXT'):prompt+='\nSetup context: '+os.environ['HYPR_USE_TASK_CONTEXT']
 (d/'prompt.txt').write_text(prompt)
 cmd=['codex','exec','--ignore-user-config','--skip-git-repo-check','--json','-C',os.environ.get('HYPR_USE_AGENT_CWD',str(here)),'-m','gpt-6-astra','-s','read-only','-c','model_reasoning_effort='+json.dumps(effort),'-c','approval_policy="never"','-c','features.shell_tool=false','-c','features.plugins=false','-c','features.multi_agent=false','-c','mcp_servers.cua_repl.command="node"','-c','mcp_servers.cua_repl.args='+json.dumps([str(root/'mcp/unified/server.mjs')]),'-c','mcp_servers.cua_repl.default_tools_approval_mode="approve"','-o',str(d/'final.txt'),'-']
 cmd[-1:-1]=['-c','mcp_servers.cua_repl.env={'+','.join(k+'='+json.dumps(v) for k,v in e.items() if k.startswith(('HYPR_USE_','HYPR_AGENT_PORTAL_')))+'}']
 (d/'execution.json').write_text(json.dumps({'model':'gpt-6-astra','reasoning_effort':effort,'command':cmd,'confine':e['HYPR_AGENT_PORTAL_CONFINE']},indent=2))
 start=time.time();stderr=(d/'stderr.txt').open('w');current=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,text=True,env=e,start_new_session=True);current.stdin.write(prompt);current.stdin.close()
 def record():
  with (d/'events.jsonl').open('w') as f:
   for line in current.stdout:
    try:event=json.loads(line)
    except ValueError:event={'raw':line}
    f.write(json.dumps({'time':time.time(),'event':event})+'\n');f.flush()
 thread=threading.Thread(target=record);thread.start();timeout=False
 try:current.wait(timeout=int(os.environ.get('HYPR_USE_TASK_TIMEOUT','180')))
 except subprocess.TimeoutExpired:
  timeout=True;halt()
  try:current.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(current.pid,signal.SIGKILL);current.wait()
 thread.join(timeout=5);stderr.close()
 check=None
 if task.get('check'):
  state=json.loads((here/'live/fixture/state.json').read_text());check=all(state.get(k)==v for k,v in task['check'].items())
 if task['id']=='24-calc-save':check=(here/'live/benchmark.ods').exists()
 row={'id':task['id'],'duration_s':time.time()-start,'exit':current.returncode,'timeout':timeout,'verified':check,'refocus':monitor.trigger.is_set()};results.append(row);(d/'result.json').write_text(json.dumps(row,indent=2));(out/'results.json').write_text(json.dumps(results,indent=2));print(json.dumps(row),flush=True)
 if monitor.trigger.is_set():break
monitor.close();(out/'focus-summary.json').write_text(json.dumps({'baseline':monitor.baseline,'violations':monitor.violations},indent=2))
