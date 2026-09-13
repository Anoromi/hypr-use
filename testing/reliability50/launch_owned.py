"""Owned child launched with Hyprland's explicit silent-workspace exec rule."""
import json,os,sys
from pathlib import Path
p=Path(sys.argv[1]);data=json.loads(p.read_text())
try:os.setsid()
except PermissionError:pass
pid=os.getpid();start=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[19]
(p.parent/'owned-process.json').write_text(json.dumps({'pid':pid,'start':start}))
os.environ.update(data['env'])
os.execvpe(data['command'][0],data['command'],os.environ)
