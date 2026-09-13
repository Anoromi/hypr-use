#!/usr/bin/env python3
import json,os,subprocess
from pathlib import Path
r=Path(__file__).resolve().parent
e=json.loads((r/'live-session/env.json').read_text());target=json.loads((r/'live-session/target.json').read_text())
clients=json.loads(subprocess.check_output(['hyprctl','-j','clients'],env=e,text=True))
assert any(c['address']==target['address'] and c['pid']==target['pid'] and c['class']=='zen-beta' and not c['xwayland'] for c in clients)
e['PATH']=str(r/'runtime-result/bin')+':'+e['PATH']
e.update(HYPR_AGENT_PORTAL_APP_POLICIES='zen-beta=full',HYPR_AGENT_PORTAL_CONFINE='class:zen-beta,address:'+target['address'],HYPR_AGENT_PORTAL_SECURITY_CONFINE_MATCH='all',HYPR_AGENT_PORTAL_CLIPBOARD='none')
os.execve(str(r/'runtime-result/bin/python3'),['python3',str(r.parent/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py')],e)
