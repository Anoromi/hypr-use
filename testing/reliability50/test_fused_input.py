import importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('portal',root/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class FusedInput(unittest.TestCase):
 def test_select_type_submit_is_one_transaction(self):
  with patch.object(b,'call_ctl',return_value={}) as call:
   result=b.type_with_keys('owned','Hi',replace_all=True,submit=True)
  call.assert_called_once_with(['keyboard','--json','owned','sequence','a:ctrl;h:shift;i:;enter:','']);self.assertEqual(result['keys'],4)
 def test_empty_text_clears_selection(self):
  with patch.object(b,'call_ctl',return_value={}) as call:b.type_with_keys('owned','',replace_all=True)
  self.assertEqual(call.call_args.args[0][4],'a:ctrl;backspace:')
 def test_invalid_text_never_selects_or_deletes(self):
  with patch.object(b,'call_ctl') as call:
   with self.assertRaises(RuntimeError):b.type_with_keys('owned','Hello 東京',replace_all=True)
   with self.assertRaises(RuntimeError):b.type_with_keys('owned','x'*4096,replace_all=True)
   call.assert_not_called()
 def test_flags_cannot_be_silently_ignored_on_other_methods(self):
  for args in [{'text':'x','method':'paste','replace_all':True},{'text':'x','method':'keys','submit':1}]:
   with self.assertRaises(RuntimeError):b.semantic_type_text(args)
if __name__=='__main__':unittest.main()
