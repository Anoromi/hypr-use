#!/usr/bin/env python3
import json,subprocess,tomllib,time
from pathlib import Path
r=Path(__file__).resolve().parent
args=['codex','exec','--json','-C',str(r.parent),'-s','read-only','-c','features.shell_tool=false','-c','mcp_servers.hypr_calc.command="python3"','-c','mcp_servers.hypr_calc.args='+json.dumps([str(r/'mcp-calc-server.py')]),'-c','mcp_servers.hypr_calc.enabled_tools='+json.dumps(['list_apps','launch_app','get_app_state','click','type_text','press_key','wait_for_window','wait_for_close','activate_menu_item','manage_window']),'-c','mcp_servers.hypr_calc.default_tools_approval_mode="approve"']
config=Path.home()/'.codex/config.toml'
if config.exists():
 for name in tomllib.loads(config.read_text()).get('mcp_servers',{}):args+=['-c',f'mcp_servers.{name}.enabled=false']
args+=['-']
(r/'calc-session/run.json').write_text(json.dumps({'started':time.time(),'command':args,'recording':'visible agent messages, tool arguments, results, screenshots; no private reasoning','setup':'Portal launch requests are prefixed with [workspace 2 silent]; CSV researched separately; all workbook creation/import/save through GUI','clipboard':'none'},indent=2))
with (r/'calc-session/thread.jsonl').open('w') as out,(r/'calc-session/thread.stderr').open('w') as err:
 x=subprocess.run(args,input=(r/'calc-prompt.txt').read_text(),text=True,stdout=out,stderr=err)
(r/'calc-session/exit.json').write_text(json.dumps({'finished':time.time(),'exit_code':x.returncode}))
raise SystemExit(x.returncode)
