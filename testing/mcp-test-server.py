#!/usr/bin/env python3
import json,os
from pathlib import Path
root=Path(__file__).resolve().parent
e=json.loads((root/'session/env.json').read_text())
e['PATH']=str(root/'runtime-result/bin')+':'+e['PATH']
e.update(HYPR_AGENT_PORTAL_APP_POLICIES='fixture.py=full',HYPR_AGENT_PORTAL_CONFINE='class:fixture.py',HYPR_AGENT_PORTAL_CLIPBOARD='none')
# Refuse to connect to the user's real compositor if the test session is absent.
runtime=Path(e['XDG_RUNTIME_DIR'])
assert runtime.parent == Path('/tmp') and runtime.name.startswith('hypr-use-')
assert (runtime/'hypr'/e['HYPRLAND_INSTANCE_SIGNATURE']/'.socket.sock').exists()
os.execve(str(root/'runtime-result/bin/python3'),['python3',str(root.parent/'vendor/hypr-agent-portal/mcp/hypr-agent-portal-mcp.py')],e)
