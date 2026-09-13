#!/usr/bin/env python3
import json,subprocess,tomllib
from pathlib import Path
root=Path(__file__).resolve().parent
args=['codex','exec','--json','--ephemeral','-C',str(root.parent),'-s','read-only','-c','features.shell_tool=false','-c','mcp_servers.hypr_agent_test.command="python3"','-c','mcp_servers.hypr_agent_test.args='+json.dumps([str(root/'mcp-test-server.py')]),'-c','mcp_servers.hypr_agent_test.enabled_tools=["list_apps","get_app_state","type_text","click","press_key"]']
config=Path.home()/'.codex/config.toml'
if config.exists():
    for name in tomllib.loads(config.read_text()).get('mcp_servers',{}):
        args+=['-c',f'mcp_servers.{name}.enabled=false']
args+=['-c','mcp_servers.hypr_agent_test.default_tools_approval_mode="approve"','-']
with (root/'codex-test.jsonl').open('w') as out,(root/'codex-test.stderr').open('w') as err:
    result=subprocess.run(args,input=(root/'codex-prompt.txt').read_text(),text=True,stdout=out,stderr=err)
raise SystemExit(result.returncode)
