"""Transport errors, deferred observations, index binding and popup protection."""
import importlib.util
from pathlib import Path
import socket
import sys
from unittest.mock import patch, Mock

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'mcp/unified'))
from control import Control
from observations import Observations
from session_events import SessionEvents

c=Control(root/'vendor/hypr-agent-portal-0.56.2/scripts/hypr-agent-portalctl')
with patch.object(c,'request',return_value='error: guard-active:locked') as req:
    assert c.run(['hyprctl','eval','ignored']).returncode==1
    req.assert_called_once()
with patch.object(c,'request',side_effect=TimeoutError('uncertain')) as req:
    try:c.run(['hyprctl','eval','ignored'])
    except TimeoutError:pass
    else:raise AssertionError('Timeout lost')
    req.assert_called_once()  # Never repeat a possibly dispatched request.

spec=importlib.util.spec_from_file_location('portal_fast_test',root/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
obs=Observations(b)
old={'index':4,'source':'atspi','controlType':'button','name':'Save','runtimeId':[0,4]}
fresh={'elements':[dict(old,index=9)]}
assert obs.rematch(old,fresh)['index']==9
for elements in [[dict(old,name='Delete')],[dict(old,runtimeId=[0,5]),dict(old,runtimeId=[0,6])]]:
    try:obs.rematch(old,{'elements':elements})
    except RuntimeError:pass
    else:raise AssertionError('Recycled or ambiguous index accepted')
before={'target':'bound','window':{'address':'bound'},'elements':[old]}
with patch.object(b,'resolve_hypr_window',return_value=before['window']),patch.object(b,'related_windows_for',return_value=[]),patch.object(b,'privacy_filtered_related_windows',side_effect=lambda x:x),patch.object(b,'merge_last_action'),patch.object(b,'build_app_snapshot',side_effect=AssertionError('Acknowledgement scanned AX')):
    after=b.snapshot_after_action('app',before,{'method':'keys'})
    assert after['observationDeferred'] and after['elements']==[]
    assert before['elements']==[old]

def event_test(changes, related):
    obj=SessionEvents.__new__(SessionEvents);obj.b=Mock();obj.b.sync_related_session.side_effect=related;obj.changed=Mock(side_effect=changes);obj.fallback=Mock(return_value=[])
    return obj

# A dialog appearing during the guard window retains its session.
obj=event_test([True],[[],[{'title':'Delayed dialog'}]])
with patch('session_events.time.monotonic',side_effect=[0,.05,.1]):
    info={};assert obj.finish('bound',info);assert info['active'];obj.b.session_action.assert_not_called()
# A broken event observer falls back to the original guarded polling.
obj=event_test([OSError('closed')],[[]])
with patch('session_events.time.monotonic',side_effect=[0,.05,.1]):
    info={};obj.finish('bound',info);obj.fallback.assert_called_once();assert info['eventFallback']=='closed'

print('No dispatch retry; strict AX rematch; deferred snapshots; delayed-dialog guard and observer fallback passed')

class Node:
    def __init__(self, role, bounds=None, parent=None, children=()):
        self.role,self.bounds,self.parent,self.children=role,bounds,parent,list(children)
    def get_parent(self):return self.parent

def bars(horizontal=27,vertical=27):
    result=[]
    for width,height,delta in [(500,12,horizontal),(12,500,vertical)]:
        old=Node('panel',dict(x=0,y=100,width=width,height=height))
        for _ in range(3):old=Node('panel',dict(x=0,y=100,width=width,height=height),old)
        bar=Node('scroll bar',dict(x=0,y=100+delta,width=width,height=height),old)
        result.append(bar)
    container=Node('panel',children=result)
    return Node('table',parent=Node('document spreadsheet',parent=container))

with patch.object(b,'atspi_role',side_effect=lambda n:n.role),patch.object(b,'atspi_extents',side_effect=lambda n:n.bounds),patch.object(b,'atspi_child_count',side_effect=lambda n:len(n.children)),patch.object(b,'atspi_child_at',side_effect=lambda n,i:n.children[i]):
    assert b.atspi_grid_translation(bars())==(0,27)
    assert b.atspi_grid_translation(bars(13,27)) is None
    assert b.atspi_grid_translation(bars(0,0)) == (0,0)
print('Grid correction requires agreement from both measured scrollbar wrappers')
