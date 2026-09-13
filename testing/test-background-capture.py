import importlib.util
import io
import contextlib
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

root = Path(__file__).resolve().parent.parent / 'vendor/hypr-agent-portal-0.56.2'
spec = importlib.util.spec_from_file_location('storage', root / 'tests/secure_screenshot_storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
ctl = storage.load('capture_ctl', root / 'scripts/hypr-agent-portalctl')
for denied in (False, True):
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        calls = []
        def dispatch(name, payload):
            calls.append(payload)
            if payload.endswith(',prepare'):
                return subprocess.CompletedProcess([], 7 if denied else 0, '', 'blocked' if denied else '')
            storage.native_fixture(ctl, directory, Path(payload.split(',')[0]))
            return subprocess.CompletedProcess([], 0, '', '')
        args = storage.screenshot_args()
        args.target = 'address:0x123'
        with patch.object(ctl, 'state_root', return_value=directory), patch.object(ctl, 'dispatch', side_effect=dispatch), patch.object(ctl.time, 'sleep') as wait, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = ctl.screenshot(args)
        assert result == (7 if denied else 0)
        assert len(calls) == (1 if denied else 2)
        assert calls[0].endswith(',address:0x123,prepare')
        assert wait.call_count == (0 if denied else 1)
print('Fresh capture preparation and denied-preparation regression tests passed')
