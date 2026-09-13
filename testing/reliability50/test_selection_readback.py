import importlib.util,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('selection',root/'vendor/hypr-agent-portal-0.56.2/mcp/text_selection.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Selection(unittest.TestCase):
 def test_delayed_readback_never_repeats_mutation(self):
  mutations=[];reads=iter([NS(start_offset=0,end_offset=0),NS(start_offset=6,end_offset=10)])
  text=NS(get_text=lambda *a:'alpha beta gamma',get_n_selections=lambda *a:0,add_selection=lambda *a:mutations.append(a) or True,get_selection=lambda *a:next(reads))
  with patch.object(m.time,'sleep'):
   result=m.select_node(NS(Text=text),NS(get_text_iface=lambda:'iface'),{'text':'beta'})
  self.assertTrue(result['ok']);self.assertEqual(len(mutations),1)
 def test_persistent_mismatch_is_error(self):
  with patch.object(m.time,'monotonic',side_effect=[0,1]):
   with self.assertRaisesRegex(ValueError,'expected.*observed'):m.wait_readback(lambda:(0,0),(6,10))
 def test_match_has_no_sleep(self):
  with patch.object(m.time,'sleep') as sleep:m.wait_readback(lambda:1,1);sleep.assert_not_called()
 def test_ambiguous_text_rejected_before_selection(self):
  with self.assertRaisesRegex(ValueError,'ambiguous'):m.selection_range('x x','x')
if __name__=='__main__':unittest.main()
