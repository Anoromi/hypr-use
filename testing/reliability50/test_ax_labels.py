import importlib.util,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('portal',root/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def node(name='',role='text',labels=(),parent=None):
 relation=NS(get_relation_type=lambda:2,get_n_targets=lambda:len(labels),get_target=lambda i:NS(get_name=lambda:labels[i]))
 return NS(get_name=lambda:name,get_role_name=lambda:role,get_relation_set=lambda:[relation] if labels else [],get_parent=lambda:parent)
class Labels(unittest.TestCase):
 def setUp(self):self.p=patch.object(b,'_ATSPI',NS(RelationType=NS(LABELLED_BY=2)));self.p.start();self.addCleanup(self.p.stop)
 def test_provider_label_and_immediate_combo_inheritance(self):
  self.assertEqual(b.atspi_input_label(node(labels=['Email']),'text'),('Email','labelled-by'))
  self.assertEqual(b.atspi_input_label(node(parent=node(role='combo box',labels=['Find:'])),'text'),('Find:','parent-combo-labelled-by'))
 def test_no_proximity_or_arbitrary_ancestor_inference(self):
  self.assertEqual(b.atspi_input_label(node(parent=node(role='panel',labels=['Wrong'])),'text'),('',''))
  self.assertEqual(b.atspi_input_label(node(labels=['Wrong']),'table cell'),('',''))
 def test_ambiguous_and_oversized_relations_do_not_choose_a_label(self):
  self.assertEqual(b.atspi_declared_label(node(labels=['A','B'])),'')
  self.assertEqual(b.atspi_declared_label(node(labels=['A']*9)),'')
  self.assertEqual(b.atspi_declared_label(node(labels=['A','A'])),'A')
if __name__=='__main__':unittest.main()
