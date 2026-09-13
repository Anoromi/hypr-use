"""Only a title-only, pre-dispatch mismatch may recapture and rematch once."""
import copy
import importlib.util
from pathlib import Path
from unittest.mock import patch

path=Path(__file__).resolve().parents[1]/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py'
spec=importlib.util.spec_from_file_location('title_recovery',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
window={'address':'0xabc','pid':41,'processStartTime':'77','class':'zen','initialClass':'zen','initialTitle':'Zen','title':'Old','at':[0,0],'size':[800,600],'atspiRootIdentity':{'title':'Old'}}
element={'source':'atspi','index':3,'runtimeId':[0,1],'controlType':'push button','name':'Back','actions':['press'],'states':['enabled']}
old={'target':'address:0xabc@41:77','window':window,'elements':[element]}
fresh=copy.deepcopy(old);fresh['window']['title']='New';fresh['window']['atspiRootIdentity']['title']='New';fresh['elements'][0]['index']=9

def reject(fn, text=None):
    try:fn()
    except RuntimeError as ex:
        if text:assert text in str(ex),str(ex)
    else:raise AssertionError('Expected rejection')

# Live guard distinguishes mutable title from a stable identity change.
with patch.object(m,'resolve_hypr_window',return_value=fresh['window']),patch.object(m,'process_start_time',return_value='77'):
    try:m.require_atspi_mutation_identity(old)
    except m.AtspiTitleDrift:pass
    else:raise AssertionError('Title drift was not classified')
root_drift=copy.deepcopy(old);root_drift['window']['atspiRootIdentity']['title']='New'
with patch.object(m,'resolve_hypr_window',return_value=window),patch.object(m,'process_start_time',return_value='77'):
    try:m.require_atspi_mutation_identity(root_drift)
    except m.AtspiTitleDrift:pass
    else:raise AssertionError('Root title drift was not classified')
for field,value in [('address','0xdef'),('pid',42),('class','other'),('initialClass','other'),('initialTitle','Other')]:
    live=copy.deepcopy(window);live[field]=value
    with patch.object(m,'resolve_hypr_window',return_value=live),patch.object(m,'process_start_time',return_value='77'):
        try:m.require_atspi_mutation_identity(old)
        except m.AtspiTitleDrift:raise AssertionError(f'{field} was considered retryable')
        except RuntimeError:pass
        else:raise AssertionError(f'{field} mismatch accepted')
with patch.object(m,'resolve_hypr_window',return_value=window),patch.object(m,'process_start_time',return_value='88'):
    reject(lambda:m.require_atspi_mutation_identity(old),'identity changed')
with patch.object(m,'resolve_hypr_window',side_effect=RuntimeError('gone')):
    reject(lambda:m.require_atspi_mutation_identity(old),'disappeared')

with patch.object(m,'require_atspi_mutation_identity',side_effect=[m.AtspiTitleDrift('title'),fresh['window']]),patch.object(m,'build_app_snapshot',return_value=fresh) as capture:
    state,target,info=m.prepare_auto_atspi_click(old,element)
    assert target['index']==9 and state is fresh and info['identityRefresh']=='title-only'
    capture.assert_called_once()
with patch.object(m,'require_atspi_mutation_identity',side_effect=m.AtspiTitleDrift('still loading')),patch.object(m,'build_app_snapshot',return_value=fresh) as capture:
    reject(lambda:m.prepare_auto_atspi_click(old,element),'still loading');capture.assert_called_once()
for candidates in [[dict(element,name='Forward')],[element,dict(element,index=8)],[dict(element,states=[])]]:
    ambiguous=copy.deepcopy(fresh);ambiguous['elements']=candidates
    with patch.object(m,'require_atspi_mutation_identity',side_effect=m.AtspiTitleDrift('title')),patch.object(m,'build_app_snapshot',return_value=ambiguous):
        reject(lambda:m.prepare_auto_atspi_click(old,element),'unique enabled')
changed=copy.deepcopy(fresh);changed['window']['pid']=42
with patch.object(m,'require_atspi_mutation_identity',side_effect=m.AtspiTitleDrift('title')),patch.object(m,'build_app_snapshot',return_value=changed):
    reject(lambda:m.prepare_auto_atspi_click(old,element),'stable identity')

# A dispatched action may have happened even when its response fails.
for result in [False,RuntimeError('child timeout')]:
    with patch.object(m,'element_snapshot_for_action',return_value=(old,element,None)),patch.object(m,'visible_element_center',return_value=(10,10)),patch.object(m,'begin_related_action_session',return_value={'begin':{'ok':True}}),patch.object(m,'finish_related_action_session') as finish,patch.object(m,'prepare_auto_atspi_click',return_value=(old,element,None)),patch.object(m,'control_overlay'),patch.object(m,'call_ctl') as pointer,patch.object(m,'atspi_do_action_isolated',side_effect=result if isinstance(result,Exception) else None,return_value=result) as action:
        reject(lambda:m.semantic_click({'app':'zen','element_index':3,'element_click_mode':'auto'}))
        action.assert_called_once();pointer.assert_not_called();finish.assert_called_once()
print('Title classification, one recapture, strict rematch, stable identity, no duplicate dispatch and cleanup passed')
