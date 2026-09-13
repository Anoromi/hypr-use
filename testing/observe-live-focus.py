import json,subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parent;e=json.loads((r/'live-session/env.json').read_text())
with (r/'live-session/focus.jsonl').open('w') as f:
    for _ in range(240):
        state={}
        for name,args in [('window',['activewindow']),('cursor',['cursorpos']),('workspace',['activeworkspace'])]:
            p=subprocess.run(['hyprctl','-j',*args],env=e,capture_output=True,text=True)
            try:state[name]=json.loads(p.stdout)
            except ValueError:state[name]={'error':p.stdout}
        f.write(json.dumps({'time':time.time(),**state})+'\n');f.flush();time.sleep(1)
