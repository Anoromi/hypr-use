"""Resident control-program adapter using Hyprland's command socket.

The existing CLI validation, native guards and dispatcher result checks remain.
Requests are never retried: an interrupted mutation may already have happened.
"""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import time


class Control:
    def __init__(self, path, timeout=10):
        loader = importlib.machinery.SourceFileLoader('hypr_use_control', str(path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.cli = importlib.util.module_from_spec(spec)
        loader.exec_module(self.cli)
        self.parser = self.cli.build_parser()
        self.timeout = timeout
        self.socket_path = (Path(os.environ['XDG_RUNTIME_DIR'])/'hypr'/
                            os.environ['HYPRLAND_INSTANCE_SIGNATURE']/'.socket.sock')
        self.provider = None
        self.provider_at = 0
        self.cli.hyprctl = lambda *args: self.run(['hyprctl', *args])
        self.cli.hyprland_config_provider = self.config_provider
        owner = self

        class Processes:
            def __getattr__(self, name):
                return getattr(subprocess, name)

            def run(self, args, **kwargs):
                if args and args[0] == 'hyprctl':
                    return owner.run(args)
                return subprocess.run(args, **kwargs)

        self.cli.subprocess = Processes()

    def request(self, command, json_output=False):
        # One socket per transaction is required by Hyprland's EOF-framed
        # protocol; the Python worker stays resident between transactions.
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(self.timeout)
            client.connect(str(self.socket_path))
            client.sendall((('j/' if json_output else '/') + command).encode())
            chunks = []
            total = 0
            while chunk := client.recv(65536):
                total += len(chunk)
                if total > 64 * 1024 * 1024:
                    raise RuntimeError('Compositor response exceeds 64 MiB')
                chunks.append(chunk)
        return b''.join(chunks).decode()

    def run(self, args):
        parts = [str(x) for x in args[1:]]
        json_output = '-j' in parts
        parts = [x for x in parts if x != '-j']
        output = self.request(' '.join(parts), json_output)
        failed = output.lstrip().lower().startswith(('error:', 'unknown request', 'unknown command'))
        return subprocess.CompletedProcess(args, 1 if failed else 0, output, '')

    def config_provider(self):
        if self.provider is None or time.monotonic() - self.provider_at > 5:
            result = self.run(['hyprctl', 'systeminfo'])
            import re
            match = re.search(r'^configProvider:\s*(\S+)', result.stdout, re.MULTILINE)
            if result.returncode or not match:
                raise RuntimeError('Could not determine compositor config provider')
            self.provider = match.group(1).lower()
            self.provider_at = time.monotonic()
        return self.provider

    def call(self, args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                parsed = self.parser.parse_args(args)
                code = parsed.func(parsed)
            except SystemExit as ex:
                code = ex.code
        if code:
            raise RuntimeError((stderr.getvalue() or stdout.getvalue()).strip() or f'Control failed: {code}')
        return json.loads(stdout.getvalue()) if stdout.getvalue().strip() else {}


def install(backend):
    control = Control(backend.find_ctl(), backend.MAX_TOOL_WAIT_SECONDS)
    if os.environ.get("HYPR_USE_NATIVE_RESIZE", "1") != "0":
        from raster import install as install_raster
        control.native_resize = install_raster(control.cli)
    backend.call_ctl = control.call
    backend.control_request = control.request
    # Indirect call allows the timing wrapper to tag native IPC separately.
    control.request = lambda *args, **kwargs: backend.control_request(*args, **kwargs)
    return control
