import sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'mcp/unified'))
from observations import Observations

class MenuRouting(unittest.TestCase):
 def route(self,element=None,**options):
  e={'index':1,'name':'Choice','controlType':'menu item','runtimeId':[0,1],'className':'gtk','source':'atspi','actions':['click']}
  e.update(element or {});state={'target':'owned','elements':[e]}
  b=NS(normalize=lambda s:str(s).lower(),element_role=lambda e:e['controlType'],lookup_element=lambda s,i:s['elements'][0],build_app_snapshot=lambda _:state,snapshot_window_query=lambda s,a:a,snapshot_after_action=lambda *a:None,atspi_snapshot_isolated=lambda *a:None,ensure_global_menu_backends=lambda:None,dbus_services_for_pid=lambda p:[],dbus_tree_paths=lambda o:[],process_start_time=lambda p:'1',SEMANTIC_TOOLS={n:lambda a:a for n in ['click','scroll','set_value','select_text','perform_secondary_action']})
  o=Observations(b);o.publish('owned',state)
  return b.SEMANTIC_TOOLS['click']({'app':'owned','element_index':'1','element_click_mode':'pointer',**options})
 def test_gtk_single_left_menu_click_uses_semantics(self):
  self.assertEqual(self.route()['element_click_mode'],'atspi')
 def test_other_toolkits_roles_and_missing_actions_retain_pointer(self):
  for e in [{'className':'Chromium'},{'className':'Gecko'},{'controlType':'entry'},{'actions':[]},{'source':'other'}]:
   self.assertEqual(self.route(e)['element_click_mode'],'pointer')
 def test_explicit_pointer_coordinates_right_and_double_clicks_are_unchanged(self):
  for options in [{'element_index':None,'x':20,'y':30},{'mouse_button':'right'},{'click_count':2}]:
   self.assertEqual(self.route(**options)['element_click_mode'],'pointer')
if __name__=='__main__':unittest.main()
