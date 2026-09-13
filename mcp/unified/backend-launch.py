import os,sys,json
from pathlib import Path
r=Path(__file__).resolve().parents[2];e=os.environ.copy();runtime=r/'testing/runtime-result'
p=r/'testing/live-session/env.json'
# Desktop apps may export a nonempty GTK4-only path without Atspi. Prepend
# the tested runtime's typelibs rather than treating any existing path as sufficient.
saved=json.loads(p.read_text()).get('GI_TYPELIB_PATH','') if p.exists() else ''
paths=[str(runtime/'lib/girepository-1.0'),*saved.split(':'),*e.get('GI_TYPELIB_PATH','').split(':')]
e['GI_TYPELIB_PATH']=':'.join(dict.fromkeys(x for x in paths if x and Path(x).is_dir()))
e['PATH']=str(runtime/'bin')+':'+e.get('PATH','')
python=runtime/'bin/python3'
os.execve(str(python),[str(python),str(Path(__file__).with_name('backend.py'))],e)
