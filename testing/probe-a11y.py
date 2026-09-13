import os,json,sys,subprocess
from pathlib import Path
r=Path(__file__).resolve().parent
if not os.environ.get('HYPR_PROBE_A11Y'):
 e=json.loads((r/'live-session/env.json').read_text());e['HYPR_PROBE_A11Y']='1';e['PATH']=str(r/'runtime-result/bin')+':'+e['PATH'];os.execve(str(r/'runtime-result/bin/python3'),['python3',__file__,*sys.argv[1:]],e)
if '--enable' in sys.argv:
 subprocess.run(['busctl','--user','set-property','org.a11y.Bus','/org/a11y/bus','org.a11y.Status','IsEnabled','b','true'],check=True)
import gi
gi.require_version('Atspi','2.0')
from gi.repository import Atspi
Atspi.init();d=Atspi.get_desktop(0)
print('apps',[(d.get_child_at_index(i).get_name(),d.get_child_at_index(i).get_process_id()) for i in range(d.get_child_count())])
for prop in ['IsEnabled','ScreenReaderEnabled']:
 p=subprocess.run(['busctl','--user','get-property','org.a11y.Bus','/org/a11y/bus','org.a11y.Status',prop],capture_output=True,text=True);print(prop,p.stdout.strip(),p.stderr.strip())
