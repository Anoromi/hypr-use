import importlib.util,unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('portal',root/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class CheckboxState(unittest.TestCase):
 def test_mixed_is_not_reported_as_unchecked(self):
  node=NS(get_state_set=lambda:NS(contains=lambda flag:flag==1),get_toolkit_name=lambda:'test',is_editable_text=lambda:False,is_text=lambda:False,is_value=lambda:False)
  with ExitStack() as stack:
   stack.enter_context(patch.object(b,'_ATSPI',NS(StateType=NS(INDETERMINATE=1))))
   for name,value in {'atspi_role':'check box','atspi_accessible_id':'','atspi_name':'Mixed','atspi_text_value':'','atspi_numeric_value':'','atspi_image_frame':{},'atspi_action_names':[],'atspi_node_is_editable':False}.items():stack.enter_context(patch.object(b,name,return_value=value))
   result=b.atspi_record_for(node,0,[],None,None,{}, {})
  self.assertIsNone(result['checked']);self.assertIn('indeterminate',result['states'])
if __name__=='__main__':unittest.main()
