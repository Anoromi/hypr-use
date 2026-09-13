import importlib.util
from pathlib import Path
r=Path(__file__).resolve().parent.parent/'vendor/hypr-agent-portal-0.56.2'
spec=importlib.util.spec_from_file_location('portal',r/'mcp/hypr-agent-portal-mcp.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
for args,want in [({'key':'ctrl+t'},('t','ctrl')),({'keys':'ctrl+t'},('t','ctrl')),({'key':'Return'},('Return','')),({'key':'minus'},('minus','')),({'key':'t','modifiers':'ctrl'},('t','ctrl')),({'key':'ctrl+shift+t'},('t','ctrl+shift')),({'key':'ctrl+t','modifiers':'shift'},('t','ctrl+shift'))]:
 assert m.key_from_args(args)==want,(args,m.key_from_args(args))
print('7 shortcut regression cases passed')
