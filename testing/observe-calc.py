import json,subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parent;e=json.loads((r/'live-session/env.json').read_text());deadline=time.monotonic()+1800
with (r/'calc-session/focus.jsonl').open('a') as f:
 while time.monotonic()<deadline and not (r/'calc-session/exit.json').exists():
  try:
   w=json.loads(subprocess.check_output(['hyprctl','-j','activewindow'],env=e,text=True,timeout=2));ws=json.loads(subprocess.check_output(['hyprctl','-j','activeworkspace'],env=e,text=True,timeout=2))
   f.write(json.dumps({'time':time.time(),'class':w.get('class'),'address':w.get('address'),'workspace':ws.get('id')})+'\n');f.flush()
  except Exception as ex:f.write(json.dumps({'error':type(ex).__name__})+'\n')
  time.sleep(.5)
