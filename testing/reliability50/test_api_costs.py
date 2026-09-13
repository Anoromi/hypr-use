"""Unified AX observations should not discover menus the API cannot expose."""
import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('observations',root/'mcp/unified/observations.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MenuCosts(unittest.TestCase):
 def backend(self):
  self.calls=[]
  def menu(window):
   self.calls.append(window)
   return {'status':'ok','items':[{'name':'Save'}]}
  return SimpleNamespace(snapshot_after_action=lambda *a:None,atspi_snapshot_isolated=lambda *a:None,
   SEMANTIC_TOOLS={k:lambda args:None for k in ['click','scroll','set_value','select_text','perform_secondary_action']},
   global_menu_for_window=menu,ensure_global_menu_backends=lambda:None,
   dbus_services_for_pid=lambda _:[],dbus_tree_paths=lambda _:[])
 def test_default_omits_unexposed_discovery(self):
  b=self.backend()
  with patch.dict('os.environ',{},clear=True):m.Observations(b)
  self.assertEqual(b.global_menu_for_window({'pid':1}),{'status':'not-requested','items':[]})
  self.assertEqual(self.calls,[])
 def test_diagnostic_switch_keeps_original_discovery(self):
  b=self.backend()
  with patch.dict('os.environ',{'HYPR_USE_GLOBAL_MENU':'1'}):m.Observations(b)
  self.assertEqual(b.global_menu_for_window({'pid':1})['items'],[{'name':'Save'}])
  self.assertEqual(len(self.calls),1)

if __name__=='__main__':unittest.main()
