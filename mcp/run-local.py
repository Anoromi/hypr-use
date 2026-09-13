#!/usr/bin/env python3
"""Launch with the already-built Nix runtime and the current desktop session."""
import json
import os
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
runtime = root / 'testing/runtime-result'
env = os.environ.copy()
# Only a library search path is reused, never saved session/socket credentials.
saved = root / 'testing/live-session/env.json'
if not env.get('GI_TYPELIB_PATH') and saved.exists():
    env['GI_TYPELIB_PATH'] = json.loads(saved.read_text()).get('GI_TYPELIB_PATH', '')
env['PATH'] = str(runtime / 'bin') + os.pathsep + env.get('PATH', '')
python = runtime / 'bin/python3'
if not python.exists():
    sys.exit('Build testing/runtime-result first, or run mcp/server.py with Python + PyGObject/AT-SPI.')
os.execve(str(python), [str(python), str(Path(__file__).with_name('server.py'))], env)
