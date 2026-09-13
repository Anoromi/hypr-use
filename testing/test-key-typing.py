"""Long key-event typing must not cancel dialogs containing a file-list table."""
import importlib.util
from pathlib import Path
from unittest.mock import patch

path=Path(__file__).resolve().parents[1]/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py'
spec=importlib.util.spec_from_file_location('key_typing',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
snapshot={'target':'qualified-save-dialog','elements':[{'controlType':'table','name':'Files'},{'controlType':'text','focused':True,'editable':True,'name':'Name'}]}
for text in ['x'*84,'alpha\nbeta','one\ttwo']:
    with patch.object(m,'current_snapshot',return_value=snapshot),patch.object(m,'control_overlay'),patch.object(m,'prepare_grid_bulk_paste',side_effect=AssertionError('Typing must not inject Escape')) as prep,patch.object(m,'type_text',return_value={'method':'keys'}) as type_text,patch.object(m,'snapshot_after_action',side_effect=lambda app,state,info:info),patch.object(m,'mcp_snapshot_result',side_effect=lambda info:info):
        args={'app':'save','text':text,'method':'keys'}
        assert m.semantic_type_text(args)=={'method':'keys'}
        type_text.assert_called_once_with(snapshot['target'],text,args)
        prep.assert_not_called()
print('Long paths, multiline and tab-separated key typing preserve dialog and input context')
