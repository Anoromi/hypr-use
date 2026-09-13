"""Close only benchmark-owned windows and disable the named temporary rule."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from monitor import Monitor, ctl

here=Path(__file__).resolve().parent
name=sys.argv[1];out=here/'cleanup'/name;out.mkdir(parents=True,exist_ok=True)
monitor=Monitor(out/'focus.jsonl',['hypr-use-bench','libreoffice-calc','soffice','zen-beta'])
closed=[]
try:
    for window in ctl('clients'):
        if window['class'] not in {'hypr-use-bench','libreoffice-calc','libreoffice-startcenter','soffice'}:continue
        pid=window['pid']
        if pid in closed:continue
        cmd=Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode()
        owned=(str(here/'fixture.py') in cmd or str(here/'live/calc-profile-fast') in cmd)
        if not owned:raise RuntimeError('Refusing to close an unrecognized application process')
        os.kill(pid,signal.SIGTERM);closed.append(pid)
    time.sleep(1)
    result=subprocess.run(['hyprctl','eval','hl.window_rule({name="hypr-use-benchmark",match={class="^(hypr-use-bench|libreoffice.*|soffice)$"}}):set_enabled(false)'],capture_output=True,text=True)
    assert result.returncode==0 and result.stdout.strip()=='ok',result.stdout
finally:monitor.close()
(out/'result.json').write_text(json.dumps({'closed_pids':closed,'refocus':monitor.violations,'active_after':ctl('activewindow').get('class')},indent=2))
print((out/'result.json').read_text())
