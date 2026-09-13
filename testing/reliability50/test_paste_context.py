"""Exercise production paste routing without reading or writing the clipboard."""
import ast,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from typing import Any

source=Path(__file__).resolve().parents[2]/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py'
def load():
 calls=[]
 env=dict(Any=Any,time=NS(sleep=lambda _:None),element_role=lambda e:e['controlType'],
  current_snapshot=lambda _:{'target':'owned','elements':[{'controlType':'table'},{'controlType':'entry','focused':True}]},
  control_overlay=lambda *a,**k:None,keyboard=lambda *a:calls.append('escape') or {},
  prefer_related_target=lambda *a:('owned',None),target_uses_xwayland=lambda *a:False,
  set_clipboard_text=lambda *a:calls.append('clipboard') or [],paste=lambda *a,**k:calls.append('paste') or {},result_text=lambda v:v)
 tree=ast.parse(source.read_text());tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'semantic_paste_text','prepare_grid_bulk_paste','snapshot_has_grid_target','text_is_bulk_paste_candidate'}]
 exec(compile(tree,str(source),'exec'),env);return env['semantic_paste_text'],calls
class PasteContext(unittest.TestCase):
 def test_legacy_default_reproduces_escape_in_an_unrelated_table_window(self):
  paste,calls=load();paste({'app':'owned','text':'x'*100});self.assertEqual(calls,['escape','clipboard','paste'])
 def test_preserved_context_never_injects_escape(self):
  paste,calls=load();result=paste({'app':'owned','text':'line one\nline two','prepare_grid':False});self.assertEqual(calls,['clipboard','paste']);self.assertNotIn('preparedForGridPaste',result)
 def test_invalid_flag_cannot_mutate_clipboard_or_input(self):
  paste,calls=load()
  with self.assertRaisesRegex(RuntimeError,'boolean'):paste({'app':'owned','text':'x'*100,'prepare_grid':'false'})
  self.assertEqual(calls,[])
if __name__=='__main__':unittest.main()
