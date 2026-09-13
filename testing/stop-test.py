#!/usr/bin/env python3
import json,os,signal,time
from pathlib import Path
root=Path(__file__).resolve().parent
p=root/'session/pids.json'
if p.exists():
    for name,pid in reversed(list(json.loads(p.read_text()).items())):
        try:
            command=Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode()
            expected={'cage':'/runtime-result/bin/cage','weston':'weston','dbus':'dbus-daemon','hyprland':str(root/'session/hyprland.conf'),'fixture':str(root/'fixture.py'),'sentinel':str(root/'sentinel.py'),'keyboard':'/runtime-result/bin/'}
            if expected[name] in command:os.killpg(pid,signal.SIGTERM)
        except (FileNotFoundError,ProcessLookupError):pass
    time.sleep(1)
