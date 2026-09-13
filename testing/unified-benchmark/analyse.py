import json,re,sys,statistics
from datetime import datetime, timezone
from pathlib import Path
here=Path(__file__).resolve().parent
phase=here/(sys.argv[1] if len(sys.argv)>1 else 'astra-baseline');rows=[]
correction=json.loads((phase/'setup-correction.json').read_text()) if (phase/'setup-correction.json').exists() else {}
def readlines(p):
 if not p.exists():return []
 rows=[]
 for x in p.read_text().splitlines():
  try:rows.append(json.loads(x))
  except ValueError:pass # A running writer may have an incomplete final line.
 return rows
for d in sorted(phase.iterdir()):
 if not d.is_dir() or not (d/'prompt.txt').exists():continue
 record=json.loads((d/'result.json').read_text()) if (d/'result.json').exists() else {'id':d.name,'running':True}
 record['excluded_setup_trial']=any(d.name.startswith(x) for x in correction.get('exclude_task_prefixes',[]))
 if record['excluded_setup_trial'] and record.get('running'):record.update(running=False,interrupted=True)
 record['review']=json.loads((d/'review.json').read_text()) if (d/'review.json').exists() else None
 wires=readlines(d/'wire.jsonl');portals=readlines(d/'portal.jsonl');events=readlines(d/'events.jsonl')
 methods={};stages={};stage_counts={};ctl_context={};dispatch={};targeting={"ax_index":0,"coordinates":0,"keys_or_paste":0};failures=[];toolms=0;image_count=0;ax_reads=0;text_chars=0;metadata_chars=0
 for w in wires:
  r=w['response'].get('result',{});toolms+=r.get('_meta',{}).get('hypr-use/timing',{}).get('total_ms',0)
  code=w['request'].get('params',{}).get('arguments',{}).get('code','')
  for m in re.findall(r'\.(getApp|getAXState|getScreenshot|getAXStateAndScreenshot|click|drag|scroll|pressKey|typeText|paste|setValue|selectText|performSecondaryAction)\s*\(',code):methods[m]=methods.get(m,0)+1
  text_chars+=sum(len(b.get('text','')) for b in r.get('content',[]) if b.get('type')=='text')
  metadata_chars+=len(json.dumps(r.get('_meta',{})))
  image_count+=sum(b.get('type')=='image' for b in r.get('content',[]))
  if r.get('isError'):failures.append('\n'.join(b.get('text','') for b in r.get('content',[]) if b.get('type')=='text')[-1500:])
 for p in portals:
  request=p['request']['params'];args=request.get('arguments',{})
  if request['name'] in {'click','drag','scroll','set_value','select_text','perform_secondary_action'}:
   if args.get('element_index') is not None:targeting['ax_index']+=1
   elif 'x' in args or 'from_x' in args:targeting['coordinates']+=1
  elif request['name'] in {'press_key','type_text','paste_text'}:targeting['keys_or_paste']+=1
  r=p.get('response',{}).get('result',{});action=r.get('structuredContent',{}).get('lastAction',{})
  if request['name'] not in {'get_app_state','get_ax_state','list_apps'} and action.get('method'):
   method=action['method'];dispatch[method]=dispatch.get(method,0)+1
  timing=r.get('_meta',{}).get('hypr-use/timing',{})
  for span in timing.get('spans',[]):
   if not span.get('failed'):stage_counts[span['stage']]=stage_counts.get(span['stage'],0)+1
   stages[span['stage']]=stages.get(span['stage'],0)+span.get('self_ms',0)
   if span['stage']=='call_ctl':
    parent=span.get('parent');context=timing['spans'][parent]['stage'] if parent is not None else 'handler/session/policy'
    ctl_context[context]=ctl_context.get(context,0)+span.get('duration_ms',0)
  if p['request']['params']['name']in {'get_app_state','get_ax_state'}:ax_reads+=1
 usage={}
 for event in events:
  if event['event'].get('type')=='turn.completed':usage=event['event'].get('usage',{})
 record.update(text_response_chars=text_chars,timing_metadata_chars=metadata_chars,js_calls=sum(w['request'].get('params',{}).get('name')=='js' for w in wires),portal_calls=len(portals),tool_s=toolms/1000,non_tool_s=max(0,record.get('duration_s',0)-toolms/1000),methods=methods,input_targeting=targeting,reported_dispatch_methods=dispatch,images_emitted=image_count,backend_state_reads=ax_reads,failures=failures,stage_self_ms=stages,stage_counts=stage_counts,portal_command_context_ms=ctl_context,usage=usage,final=(d/'final.txt').read_text() if (d/'final.txt').exists() else '')
 rows.append(record)
focus=readlines(phase/'focus.jsonl')
coverage={'first_record':focus[0]['time'] if focus else None,'last_record':focus[-1]['time'] if focus else None,'samples':sum(x['kind']=='sample' for x in focus),'observer_errors':[x for x in focus if x['kind']=='observer-error'],'active_changes':sum(x['kind']=='activewindowv2' for x in focus),'opened_windows':[x['data'] for x in focus if x['kind']=='openwindow'],'discovery':'Initial class inventory, openwindow events, and active-window class polling. No persisted initial target inventory.'}
if focus:
 coverage.update(first_record_utc=datetime.fromtimestamp(focus[0]['time'],timezone.utc).isoformat(),last_record_utc=datetime.fromtimestamp(focus[-1]['time'],timezone.utc).isoformat(),recorded_span_s=focus[-1]['time']-focus[0]['time'])
summary={'focus_coverage':coverage,'phase':phase.name,'tasks':rows,'completed':sum(not r.get('running') and not r.get('excluded_setup_trial') for r in rows),'verified_pass':sum(r.get('verified') is True for r in rows),'verified_fail':sum(r.get('verified') is False for r in rows),'reviewed_pass':sum((r.get('review') or {}).get('outcome')=='pass' for r in rows),'refocus_count':len([x for x in readlines(phase/'focus.jsonl') if x['kind']=='refocus'])}
(phase/'metrics.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k not in {'tasks','focus_coverage'}}));print([(x['id'],round(x.get('duration_s',0),1),len(x['failures'])) for x in rows])
