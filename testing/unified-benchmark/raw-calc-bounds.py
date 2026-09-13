"""Read raw Calc table/header bounds without sending input."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('bounds_portal',root/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
assert b.atspi_available(),b.atspi_init_error()
clients=json.loads(subprocess.check_output(['hyprctl','-j','clients']))
window=next(w for w in clients if w['class']=='libreoffice-calc')
cmd=Path(f"/proc/{window['pid']}/cmdline").read_bytes()
assert b'calc-profile-fast-validation' in cmd
app=next(a for a in b.atspi_iter_apps() if b.atspi_pid(a)==window['pid'])
_,frame=b.atspi_match_window(app,window)
result={'window':window,'root':b.atspi_extents(frame),'tables':[],'near_grid':[]};budget=[2000]
def node(n):return {'name':b.atspi_name(n),'role':b.atspi_role(n),'bounds':b.atspi_extents(n)} if n else None
def walk(n,depth=0):
 if depth>15 or budget[0]<=0:return
 budget[0]-=1
 bounds=b.atspi_extents(n)
 if bounds and (110<=bounds['y']<=180 or 'header' in b.atspi_role(n) or b.atspi_role(n)=='scroll bar'):
  record=node(n)
  if b.atspi_role(n)=='scroll bar':
   ancestor=n;record['ancestors']=[]
   for _ in range(6):
    ancestor=b.atspi_safe(ancestor.get_parent) if ancestor else None
    if ancestor:record['ancestors'].append(node(ancestor))
  result['near_grid'].append(record)
 table=b.atspi_safe(n.get_table_iface)
 if table:
  rows=b.atspi_safe(lambda:b._ATSPI.Table.get_n_rows(table),0)
  if rows>1000:
   record=node(n);record['rows']=rows
   record['column_header']=node(b.atspi_safe(lambda:b._ATSPI.Table.get_column_header(table,0)))
   record['row_header']=node(b.atspi_safe(lambda:b._ATSPI.Table.get_row_header(table,0)))
   record['cells']=[node(b.atspi_safe(lambda row=row:b._ATSPI.Table.get_accessible_at(table,row,0))) for row in [0,1,4]]
   record['parent']=node(b.atspi_safe(n.get_parent))
   result['tables'].append(record);return
 for i in range(min(b.atspi_child_count(n),200)):
  child=b.atspi_child_at(n,i)
  if child:walk(child,depth+1)
walk(frame)
print(json.dumps(result,indent=2))
