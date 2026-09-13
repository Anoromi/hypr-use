"""Three separate browser profiles and fresh agent threads, no restore preflight."""
import hashlib,json,os,signal,subprocess,sys,tempfile,time
from pathlib import Path
from monitor import Monitor,ctl
here=Path(__file__).resolve().parent;root=here.parents[1]
series_name=os.environ.get('HYPR_USE_SERIES_NAME','restore-clean-series')
phase_prefix=os.environ.get('HYPR_USE_PHASE_PREFIX','astra-restore-clean')
series=here/series_name;series.mkdir(exist_ok=False)
base=os.environ.copy()
# Do not allow inherited experiment hints or old logs to enter the subprocesses.
for key in list(base):
 if key.startswith('HYPR_USE_') or key.startswith('HYPR_AGENT_PORTAL_'):base.pop(key)
results=[]
for n in range(1,4):
 phase=f'{phase_prefix}-{n}';p=here/phase
 cwd=Path(tempfile.mkdtemp(prefix='hypr-use-clean-agent-'));(cwd/'AGENTS.md').write_text('Always be brief.\n')
 env=base|{'HYPR_USE_RESTORE_PHASE':phase,'HYPR_USE_RESTORE_PREFLIGHT':'0','HYPR_USE_REASONING_EFFORT':'xhigh','HYPR_USE_AGENT_CWD':str(cwd),'HYPR_USE_TASK_FILE':str(p/'tasks.json')}
 try:
  subprocess.run([sys.executable,str(here/'restore-tab-setup.py')],env=env,check=True,timeout=150)
  (p/'tasks.json').write_text(json.dumps([{'id':'restore-last-tab','app':'hypr-use-restore-bench','prompt':'Can you make my computer bring back the last tab I shut down?'}],indent=2))
  files=list((root/'mcp/unified').glob('*.py'))+list((root/'mcp/unified').glob('*.mjs'))+[here/'run.py',here/'monitor.py',here/'restore-tab-setup.py',root/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py',root/'vendor/hypr-agent-portal-0.56.2/scripts/hypr-agent-portalctl']
  (p/'manifest.json').write_text(json.dumps({'model':'gpt-6-astra','reasoning_effort':'xhigh','restore_preflight':False,'agent_cwd':str(cwd),'initial_cwd_files':[x.name for x in cwd.iterdir()],'source_hashes':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},'notes':'Fresh process, browser profile, thread and empty task directory except brief AGENTS instruction. Shared OS caches and provider prompt caching are not disabled.'},indent=2))
  subprocess.run([sys.executable,str(here/'run.py'),phase,'restore-last-tab'],env=env,check=True,timeout=210)
  subprocess.run([sys.executable,str(here/'restore-tab-grade.py')],env=env,check=True,timeout=20)
  subprocess.run([sys.executable,str(here/'analyse.py'),phase],env=env,check=True,timeout=20)
  r=json.loads((p/'restore-last-tab/result.json').read_text());r['review']=json.loads((p/'restore-last-tab/review.json').read_text());results.append(r)
 finally:
  if (p/'owned-browser.json').exists():
   owned=json.loads((p/'owned-browser.json').read_text());m=Monitor(p/'cleanup-focus.jsonl',['hypr-use-restore-bench'])
   try:
    proc=Path(f"/proc/{owned['pid']}/cmdline")
    if proc.exists():
     assert owned['profile'] in proc.read_bytes().decode(errors='replace');os.kill(owned['pid'],signal.SIGTERM)
     for _ in range(30):
      if not any(w.get('pid')==owned['pid'] for w in ctl('clients')):break
      time.sleep(.1)
    command='hl.window_rule({name="hypr-use-restore-benchmark",match={class="^hypr-use-restore-bench$"}}):set_enabled(false)'
    x=subprocess.run(['hyprctl','eval',command],capture_output=True,text=True);assert x.stdout.strip()=='ok',x.stdout
    (p/'cleanup.json').write_text(json.dumps({'refocus':m.violations,'active_after':ctl('activewindow').get('class')},indent=2))
   finally:m.close()
 (series/'results.json').write_text(json.dumps(results,indent=2))
 if results[-1]['refocus']:break
print(json.dumps(results),flush=True)
