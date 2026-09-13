import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'mcp'))
sys.path.insert(0, str(ROOT / 'vendor/hypr-agent-portal-0.56.2/mcp'))
from server import Adapter, CONTRACT, load_backend
from text_selection import selection_range, select_node

class Backend:
    def __init__(self): self.calls = []
    def tool_definitions(self): return CONTRACT
    def handle(self, msg):
        self.calls.append(msg)
        return {'jsonrpc':'2.0','id':msg.get('id'),'result':{'content':[{'type':'image','data':'fake','mimeType':'image/png'}], 'isError':True, '_meta':{'test':'preserved'}}}

class Compatibility(unittest.TestCase):
    def setUp(self):
        self.b = Backend()
        self.a = Adapter(self.b, {'Firefox':'zen'})
    def call(self, name, args):
        return self.a.handle({'jsonrpc':'2.0','id':7,'method':'tools/call','params':{'name':name,'arguments':args,'_meta':{'thread':'test'}}})
    def test_contract_and_policy_discovery(self):
        self.assertEqual(len(CONTRACT),10)
        self.b.tool_definitions = lambda: [CONTRACT[0]]
        out=self.a.handle({'jsonrpc':'2.0','id':1,'method':'tools/list'})
        self.assertEqual(out['result']['tools'],[CONTRACT[0]])
    def test_all_tools_delegate_through_policy(self):
        for tool in CONTRACT:
            properties=tool['inputSchema']['properties']
            args={k: (properties[k].get('enum',['down'])[0] if k=='direction' else 1 if properties[k]['type']=='number' else '1') for k in tool['inputSchema']['required']}
            out=self.call(tool['name'],args)
            self.assertEqual(self.b.calls[-1]['params']['name'],tool['name'])
            self.assertTrue(out['result']['isError'])
            self.assertEqual(out['result']['_meta'],{'test':'preserved'})
    def test_alias_keys_and_metadata(self):
        self.call('press_key',{'app':'Firefox','key':'super+shift+t'})
        self.assertEqual(self.b.calls[-1]['params']['arguments'],{'app':'zen','key':'ctrl+shift+t'})
        self.assertEqual(self.b.calls[-1]['params']['_meta'],{'thread':'test'})
    def test_bad_args_and_hidden_bypass(self):
        for name,args in [('computer',{}),('click',{'app':'zen','x':True}),('type_text',{'app':'zen'}),('click',{'app':'zen','permission_mode':'full'}),('click',{'app':'zen','x':float('nan')})]:
            self.assertTrue(self.call(name,args)['result']['isError'])
        self.assertEqual(self.b.calls,[])
    def test_notification_cannot_mutate(self):
        self.a.handle({'jsonrpc':'2.0','method':'tools/call','params':{'name':'type_text','arguments':{'app':'zen','text':'oops'}}})
        self.assertEqual(self.b.calls,[])
    def test_real_backend_selection_is_mutating(self):
        b=load_backend()
        self.assertIn('select_text',b.FULL_LEVEL_ACTIONS)
        self.assertIn('select_text',b.SEMANTIC_TOOLS)
        self.assertIn('select_text',{t['name'] for t in b.tool_definitions()})
    def test_selection_routes_with_guard_and_identity(self):
        b=load_backend(); events=[]
        previous={'target':'window'}; fresh={'target':'window'}
        b.current_snapshot=lambda app:previous
        b.snapshot_window_query=lambda snap,app:'window'
        b.build_app_snapshot=lambda app:fresh
        b.lookup_element=lambda snap,index:{'runtimeId':[0,1]}
        b.refind_element_in_snapshot=lambda *args:({'runtimeId':[0,1]}, {})
        b.require_atspi_mutation_identity=lambda snap: events.append('identity') or {'pid':1}
        b.begin_related_action_session=lambda target: events.append('begin') or {'begin':{'ok':True}}
        b.atspi_child_action=lambda *args,**kw: events.append(('child',kw)) or {'ok':True}
        b.finish_related_action_session=lambda *args:events.append('finish')
        b.snapshot_after_action=lambda *args:args[-1]
        b.mcp_snapshot_result=lambda value:value
        b.semantic_select_text({'app':'zen','element_index':'1','text':'hello'})
        self.assertEqual(events[0:2],['identity','begin'])
        self.assertEqual(events[2][1]['runtime_id'],[0,1])
        self.assertEqual(events[3],'finish')

class TextSelection(unittest.TestCase):
    def test_disambiguation_and_unicode(self):
        self.assertEqual(selection_range('😀 x abc x def','x',suffix=' def'),(8,9))
        for content,text in [('x x','x'),('abc','z'),('abc','')]:
            with self.assertRaises(ValueError):selection_range(content,text)
    def test_select_and_caret(self):
        class Text:
            selected=None; caret=0
            @staticmethod
            def get_text(*args):return 'a 😀 b'
            @classmethod
            def get_n_selections(cls,*args):return int(cls.selected is not None)
            @classmethod
            def add_selection(cls,iface,start,end):cls.selected=(start,end); return True
            @classmethod
            def get_selection(cls,*args):return SimpleNamespace(start_offset=cls.selected[0],end_offset=cls.selected[1])
            @classmethod
            def remove_selection(cls,*args):cls.selected=None;return True
            @classmethod
            def set_caret_offset(cls,iface,offset):cls.caret=offset;return True
            @classmethod
            def get_caret_offset(cls,*args):return cls.caret
        node=SimpleNamespace(get_text_iface=lambda:object()); atspi=SimpleNamespace(Text=Text)
        self.assertTrue(select_node(atspi,node,{'text':'😀'})['ok'])
        self.assertEqual(Text.selected,(2,3))
        self.assertTrue(select_node(atspi,node,{'text':'😀','selection':'cursor_after'})['ok'])
        self.assertEqual(Text.caret,3)

if __name__=='__main__':unittest.main()
