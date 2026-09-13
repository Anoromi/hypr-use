"""Read declared AT-SPI relationships of one controller-owned dialog; no input."""
import importlib.util,json,sys,os
from pathlib import Path
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('portal',root/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
os.environ[b.ATSPI_CHILD_ENV]="1"
error=b.atspi_init_error();assert error is None,error
window=json.loads(Path(sys.argv[1]).read_text());resolved=b.atspi_resolve_window(window);assert resolved
rows=[]
def visit(node,path):
 relations=[]
 for r in node.get_relation_set():
  relations.append({'type':str(r.get_relation_type()),'targets':[{'name':b.atspi_name(r.get_target(i)),'role':b.atspi_role(r.get_target(i))} for i in range(r.get_n_targets())]})
 rows.append({'path':path,'name':b.atspi_name(node),'role':b.atspi_role(node),'relations':relations})
 for i in range(b.atspi_child_count(node)):visit(b.atspi_child_at(node,i),path+[i])
visit(resolved[2],[resolved[1]])
Path(sys.argv[2]).write_text(json.dumps(rows,indent=2))
