"""Observe popup events while the existing native workspace guard is armed."""
import os
from pathlib import Path
import select
import socket
import time


class SessionEvents:
    def __init__(self, backend):
        self.b = backend
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        path = Path(os.environ['XDG_RUNTIME_DIR'])/'hypr'/os.environ['HYPRLAND_INSTANCE_SIGNATURE']/'.socket2.sock'
        self.socket.connect(str(path))
        self.socket.setblocking(False)
        self.pending = b''
        self.fallback = backend.finish_related_action_session
        backend.finish_related_action_session = self.finish

    def changed(self, timeout):
        ready, _, _ = select.select([self.socket], [], [], max(0, timeout))
        if not ready:
            return False
        data = self.socket.recv(65536)
        if not data:
            raise RuntimeError('Compositor event socket closed')
        self.pending += data
        lines = self.pending.split(b'\n')
        self.pending = lines.pop()
        return any(line.startswith((b'openwindow>>', b'closewindow>>')) for line in lines)

    def finish(self, target, info):
        try:
            # Preserve the previous 400ms delayed-popup protection window.
            # The native early-map hook is already active from session begin.
            deadline = time.monotonic() + .4
            related = self.b.sync_related_session(target, info)
            while not related and time.monotonic() < deadline:
                if self.changed(deadline - time.monotonic()):
                    related = self.b.sync_related_session(target, info)
            if not related:
                # Final sync covers a map racing the end of the observation.
                related = self.b.sync_related_session(target, info)
            info['active'] = bool(related)
            info['observationMode'] = 'compositor-events'
            if not related:
                info['end'] = self.b.session_action('end', target)
            return related
        except (OSError, RuntimeError) as ex:
            info['eventFallback'] = str(ex)
            return self.fallback(target, info)
