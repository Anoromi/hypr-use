"""AX-only reads must not render images or pretend pixels were captured."""
import importlib.util,os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('portal',root/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
window={'address':'fixture','pid':os.getpid(),'at':[-840,3],'size':[1316,1119],'class':'fixture','title':'Fixture','workspace':{'id':902}}
b.resolve_hypr_window=lambda query:dict(window)
b.related_windows_for=lambda target:[]
b.global_menu_for_window=lambda window:{}
b.atspi_snapshot_isolated=lambda window,shot:{'status':'ok','elements':[],'treeLines':[]}
b.screenshot_for_window=lambda window:(_ for _ in ()).throw(AssertionError('AX-only observation rendered a screenshot'))
b.SNAPSHOT_INCLUDE_IMAGES=False
snapshot=b.build_app_snapshot('fixture');result=b.mcp_snapshot_result(snapshot)
assert not any(x['type']=='image' for x in result['content'])
assert snapshot['screenshot']['captureKind']=='geometry-only'
assert snapshot['screenshot']['sha256'] is None
assert snapshot['screenshot']['logicalBounds']['x']==-840
assert snapshot['elements'][0]['frame']['x']==0
print('AX-only capture and coordinate provenance passed')
