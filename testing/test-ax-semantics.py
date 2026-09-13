"""Interface availability does not imply editable content in Firefox."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
p=Path(__file__).resolve().parents[1]/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py';s=importlib.util.spec_from_file_location('b',p);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
n=SimpleNamespace(is_editable_text=lambda:True,is_text=lambda:True)
with patch.object(b,'_ATSPI',SimpleNamespace(StateType=SimpleNamespace(EDITABLE='editable',FOCUSED='focused'))),patch.object(b,'atspi_state_contains',side_effect=lambda node,state:state=='focused'):
 assert not b.atspi_node_is_editable(n)
with patch.object(b,'_ATSPI',SimpleNamespace(StateType=SimpleNamespace(EDITABLE='editable',FOCUSED='focused'))),patch.object(b,'atspi_state_contains',side_effect=lambda node,state:state=='editable'):
 assert b.atspi_node_is_editable(n)
 assert not b.atspi_node_is_editable(n,focused_only=True)
for value,expected in [('\ufffc'*10,''),('Name \ufffc','Name \ufffc'),('Read this','Read this')]:
 text=SimpleNamespace(get_character_count=lambda iface:len(value),get_text=lambda iface,a,z:value)
 node=SimpleNamespace(is_text=lambda:True,get_text_iface=lambda:object())
 with patch.object(b,'_ATSPI',SimpleNamespace(Text=text)):
  assert b.atspi_text_value(node)==expected
print('Editable state distinguishes browser controls; readable text is preserved.')

from contextlib import ExitStack
# A Firefox URL suggestion supports EditableText but is not editable. Correct
# metadata must not silently switch its established background pointer route.
element={'index':72,'name':'https://www.google.com/ — Visit','source':'atspi','controlType':'list item','actions':['click'],'editable':False,'supportsEditableText':True}
with ExitStack() as stack:
 def patcher(name,**kw):return stack.enter_context(patch.object(b,name,**kw))
 patcher('element_snapshot_for_action',return_value=({'target':'bound'},element,{}))
 patcher('visible_element_center',return_value=(400,300))
 patcher('begin_related_action_session',return_value={'begin':{'ok':True}})
 finish=patcher('finish_related_action_session')
 semantic=patcher('atspi_do_action_isolated',side_effect=AssertionError('Must retain pointer route'))
 patcher('pointer_ctl_args',return_value=(['pointer','bound'],{}))
 pointer=patcher('call_ctl',return_value={'ok':True})
 patcher('snapshot_after_action',side_effect=lambda app,snapshot,info:info)
 patcher('mcp_snapshot_result',side_effect=lambda info:info)
 result=b.semantic_click({'app':'app','element_index':72,'element_click_mode':'auto'})
 assert result['method']=='pointer';pointer.assert_called_once();semantic.assert_not_called();finish.assert_called_once()
print('Correct metadata retains the existing guarded pointer route for Firefox suggestions.')
