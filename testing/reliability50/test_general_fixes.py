"""Exercise production functions without requiring a live AT-SPI desktop."""
import ast,time,unittest,math,re
from pathlib import Path
from types import SimpleNamespace as NS
from typing import Any

source=Path(__file__).resolve().parents[2]/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py'
names={'atspi_document_coordinate_scale','atspi_action_names','atspi_numeric_value','atspi_confirmed_empty_text','semantic_press_key','atspi_render_tree','atspi_set_node_value','keyboard_sequence','type_with_keys'}
def safe(f,default=None):
 try:return f()
 except Exception:return default
def load(**extra):
 env=dict(Any=Any,time=time,math=math,re=re,atspi_safe=safe,**extra)
 tree=ast.parse(source.read_text());tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 exec(compile(tree,str(source),'exec'),env);return env

class GeneralFixes(unittest.TestCase):
 def test_spin_control_commits_numeric_value_instead_of_display_text(self):
  calls=[];env=load(_ATSPI=NS(Value=NS(set_current_value=lambda _,v:calls.append(v) or True,get_current_value=lambda _:calls[-1])))
  node=NS(is_value=lambda:True,get_value_iface=lambda:object())
  self.assertTrue(env['atspi_set_node_value'](node,'3'));self.assertEqual(calls,[3.0])
  self.assertFalse(env['atspi_set_node_value'](node,'invalid'));self.assertEqual(calls,[3.0])
 def test_provider_acknowledgement_without_change_is_failure(self):
  env=load(_ATSPI=NS(Value=NS(set_current_value=lambda *_:True,get_current_value=lambda _:0)))
  node=NS(is_value=lambda:True,get_value_iface=lambda:object())
  self.assertFalse(env['atspi_set_node_value'](node,'2026'))
 def test_whole_string_uses_one_keyboard_transaction(self):
  calls=[];env=load(call_ctl=lambda args:calls.append(args) or {},key_for_char=lambda c:(c,'') if c.isascii() else None)
  result=env['type_with_keys']('owned','2026');self.assertEqual(len(calls),1)
  self.assertEqual(calls[0][3:],["sequence","2:;0:;2:;6:",""]);self.assertEqual(result['keyboardTransactions'],1)
  with self.assertRaises(RuntimeError):env['type_with_keys']('owned','2東京')
  self.assertEqual(len(calls),1)
 def test_sequence_validates_delimiters_before_any_dispatch(self):
  calls=[];env=load(call_ctl=lambda args:calls.append(args))
  with self.assertRaises(RuntimeError):env['keyboard_sequence']('owned',[('a',''),('b;enter:','')])
  self.assertEqual(calls,[])
 def test_text_control_retains_editable_text_behavior(self):
  calls=[];env=load(_ATSPI=NS(EditableText=NS(set_text_contents=lambda _,v:calls.append(v) or True)))
  node=NS(is_value=lambda:False,is_editable_text=lambda:True,get_editable_text_iface=lambda:object())
  self.assertTrue(env['atspi_set_node_value'](node,'Inventory'));self.assertEqual(calls,['Inventory'])
 def test_document_coordinates_only_when_full_viewport(self):
  scale=load()['atspi_document_coordinate_scale'];root=dict(x=0,y=0,width=1757,height=1119)
  self.assertAlmostEqual(scale(dict(x=0,y=139,width=2812,height=1652),root),1.6,places=2)
  for doc in [dict(x=0,y=87,width=1757,height=1032),dict(x=0,y=87,width=2812,height=8000),dict(x=0,y=87,width=2812,height=1032),dict(x=64,y=139,width=2812,height=1652)]:self.assertIsNone(scale(doc,root))
 def test_unsupported_interfaces_are_not_called(self):
  env=load();node=NS(is_action=lambda:False,is_value=lambda:False,is_text=lambda:False)
  self.assertEqual(env['atspi_action_names'](node),[]);self.assertEqual(env['atspi_numeric_value'](node),'');self.assertFalse(env['atspi_confirmed_empty_text'](node))
 def test_failed_text_read_is_unknown_not_empty(self):
  def fail(_):raise RuntimeError('disconnected')
  env=load(_ATSPI=NS(Text=NS(get_character_count=fail)));node=NS(is_text=lambda:True,get_text_iface=lambda:object())
  self.assertFalse(env['atspi_confirmed_empty_text'](node))
 def test_keyboard_uses_bound_window_without_scroll_coordinates(self):
  calls=[];env=load(current_snapshot=lambda _:dict(target='owned'),key_from_args=lambda _:('a',['ctrl']),control_overlay=lambda *a,**k:None,keyboard=lambda *a:calls.append(a) or {},snapshot_after_action=lambda *a:{},mcp_snapshot_result=lambda x:x)
  env['semantic_press_key']({'app':'owned'});self.assertEqual(calls,[('owned','a',['ctrl'])])
 def test_grid_summary_preserves_zero_nonzero_and_selected_cells(self):
  cells=[NS(text='',number='0.0',selected=False,name=str(i)) for i in range(20)]
  cells[15].text='0';cells[16].number='7';cells[17].selected=True;cells[18].text=None
  root=NS(name='grid',is_table=lambda:True,get_table_iface=lambda:cells)
  for cell in cells:cell.is_table=lambda:False
  bounds=dict(x=0,y=0,width=100,height=100)
  def record(node,index,path,*_):return dict(index=index,localizedControlType='table' if node is root else 'table cell',controlType='',name=node.name,value=getattr(node,'number',''),automationId='',frame=None,actions=[])
  env=load(_ATSPI=NS(StateType=NS(SELECTED='selected',FOCUSED='focused'),Table=NS(get_n_rows=lambda _:1,get_n_columns=lambda _:20,get_accessible_at=lambda _,r,c:cells[c],get_index_at=lambda _,r,c:c)),normalize=lambda s:s,atspi_extents=lambda _:bounds,atspi_role=lambda _:'table',atspi_node_is_currently_visible=lambda *_:True,atspi_record_for=record,atspi_child_count=lambda _:0,rects_overlap=lambda *a,**k:True,corrected_large_grid_cell_bounds=lambda b,*a,**k:(b,None),atspi_state_contains=lambda n,s:getattr(n,'selected',False) if s=='selected' else False)
  env['atspi_confirmed_empty_text']=lambda n:n.text=='';env['atspi_numeric_value']=lambda n:n.number
  records,lines,_,_=env['atspi_render_tree'](root,[],{},dict(xwayland=False))
  retained={r['name'] for r in records}
  for i in [15,16,17,18]:self.assertIn(str(i),retained)
  self.assertNotIn('14',retained);self.assertTrue(any('numeric value 0.0' in s for s in lines));self.assertTrue(any('summarized: 4' in s for s in lines))

if __name__=='__main__':unittest.main()
