#!/usr/bin/env python3
import json,subprocess,tomllib
from pathlib import Path
root=Path(__file__).resolve().parent
args=['codex','exec','--json','--ephemeral','-C',str(root.parent),'-s','read-only','-c','features.shell_tool=false','-c','mcp_servers.hypr_zen_live.command="python3"','-c','mcp_servers.hypr_zen_live.args='+json.dumps([str(root/'mcp-live-server.py')]),'-c','mcp_servers.hypr_zen_live.enabled_tools=["list_apps","get_app_state","type_text","press_key","click"]']
config=Path.home()/'.codex/config.toml'
if config.exists():
    for name in tomllib.loads(config.read_text()).get('mcp_servers',{}):
        args+=['-c',f'mcp_servers.{name}.enabled=false']
args+=['-c','mcp_servers.hypr_zen_live.default_tools_approval_mode="approve"','-']
with (root/'live-session/codex.jsonl').open('w') as out,(root/'live-session/codex.stderr').open('w') as err:
    result=subprocess.run(args,input=(root/'zen-prompt.txt').read_text(),text=True,stdout=out,stderr=err)
raise SystemExit(result.returncode)
