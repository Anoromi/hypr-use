"""Controlled Writer dialog label diagnostics on a fresh owned document."""
import json, os, shlex, signal, subprocess, sys, time
from pathlib import Path
here = Path(__file__).resolve().parent
root = here.parents[1]
sys.path.insert(0, str(here.parent / 'unified-benchmark'))
from monitor import Monitor, ctl
from catalog import catalog
from native_runtime import native_runtime
import hashlib
import odf

out = here / 'diagnostics' / sys.argv[1]
out.mkdir(parents=True, exist_ok=False)
native=native_runtime(root)
files=[*root.joinpath('mcp/unified').glob('*.py'),*root.joinpath('mcp/unified').glob('*.mjs'),*root.joinpath('vendor/hypr-agent-portal-0.56.2/mcp').glob('*.py'),Path(__file__),here/'inspect_ax_relations.py',Path(native['path'])]
source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(out/'manifest.json').write_text(json.dumps({'native_runtime':native,'source_hashes':source_hashes},indent=2))
classes = ['libreoffice-calc', 'libreoffice-writer', 'libreoffice-startcenter', 'soffice']
assert not any(w['class'] in classes for w in ctl('clients'))
monitor = Monitor(out / 'focus.jsonl', classes)
owned = None
server = None
results = []
observation_results = []

def stop():
    if server and server.poll() is None:
        os.killpg(server.pid, signal.SIGTERM)
    if owned:
        try:
            fields = Path(f"/proc/{owned['pid']}/stat").read_text().split(') ', 1)[1].split()
            if fields[19] == owned['start']:
                os.killpg(owned['pid'], signal.SIGTERM)
        except ProcessLookupError:
            pass
        except FileNotFoundError:
            pass

monitor.callback = stop
try:
    for case in sys.argv[2:] or ['labels']:
        assert not monitor.trigger.is_set()
        monitor.stage = case
        d = out / case
        d.mkdir()
        task = next(t for t in catalog() if t['id'] == '43-writer-replace')
        user = d / 'profile/user'
        user.mkdir(parents=True)
        (user / 'registrymodifications.xcu').write_text('<oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Office.Common/Misc"><prop oor:name="FirstRun" oor:op="fuse"><value>false</value></prop><prop oor:name="ShowTipOfTheDay" oor:op="fuse"><value>false</value></prop></item></oor:items>')
        doc = d / 'document.odt'
        odf.seed(doc, 'writer', task['seed'])
        assert not odf.inspect(doc, 'writer', task['check'])['passed']
        env = {k: v for k, v in os.environ.items() if not k.startswith(('HYPR_USE_', 'HYPR_AGENT_PORTAL_'))}
        saved = json.loads((root / 'testing/live-session/env.json').read_text())
        env.update({k: saved[k] for k in ['GI_TYPELIB_PATH', 'XDG_DATA_DIRS'] if saved.get(k)})
        env.update(GTK_MODULES='gail:atk-bridge', SAL_USE_VCLPLUGIN='gtk3', GDK_BACKEND='wayland', NO_AT_BRIDGE='0', SAL_DISABLE_OPENCL='1')
        rule = 'hl.window_rule({name="hypr-use-writer-label-probe",match={class="^(libreoffice.*|soffice)$"},no_initial_focus=true,suppress_event="activate activatefocus",workspace="902 silent"}):set_enabled(true)'
        assert subprocess.check_output(['hyprctl', 'eval', rule], text=True).strip() == 'ok'
        cmd = ['libreoffice', '-env:UserInstallation=' + (d / 'profile').as_uri(), '--norestore', '--nofirststartwizard', str(doc)]
        (d / 'launch.json').write_text(json.dumps({'command': cmd, 'env': {k: env[k] for k in ['GI_TYPELIB_PATH', 'XDG_DATA_DIRS', 'SAL_USE_VCLPLUGIN', 'GDK_BACKEND', 'NO_AT_BRIDGE', 'SAL_DISABLE_OPENCL', 'GTK_MODULES'] if k in env}}))
        launch = '[workspace 902 silent] ' + shlex.join([sys.executable, str(here / 'launch_owned.py'), str(d / 'launch.json')]) + ' > ' + shlex.quote(str(d / 'app.log')) + ' 2>&1'
        assert subprocess.check_output(['hyprctl', 'eval', 'hl.dispatch(hl.dsp.exec_cmd(' + json.dumps(launch) + '))'], text=True).strip() == 'ok'
        for _ in range(150):
            if (d / 'owned-process.json').exists():
                owned = json.loads((d / 'owned-process.json').read_text())
            windows = [w for w in ctl('clients') if w['class'] in classes]
            if windows:
                break
            time.sleep(.1)
        assert windows and all(w['workspace']['id'] == 902 for w in windows)
        time.sleep(2)
        env.update(HYPR_AGENT_PORTAL_PERMISSION_MODE='full', HYPR_AGENT_PORTAL_APPROVAL_POLICY='never', HYPR_AGENT_PORTAL_CONFINE=','.join('class:' + c for c in classes), HYPR_USE_PORTAL_LOG=str(d / 'portal.jsonl'))
        server = subprocess.Popen(['node', str(root / 'mcp/unified/server.mjs')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=(d / 'stderr.txt').open('w'), text=True, env=env, start_new_session=True)
        steps = []
        def js(code):
            assert not monitor.trigger.is_set()
            begin = time.monotonic()
            server.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': len(steps) + 1, 'method': 'tools/call', 'params': {'name': 'js', 'arguments': {'code': code, 'timeout_ms': 30000}}}) + '\n')
            server.stdin.flush()
            result = json.loads(server.stdout.readline())
            steps.append({'code': code, 'seconds': time.monotonic() - begin, 'error': result['result'].get('isError', False)})
            (d / f'response-{len(steps)}.json').write_text(json.dumps(result))
            assert not steps[-1]['error'], str(result)[:300]
        def snapshot():
            for line in reversed((d / 'portal.jsonl').read_text().splitlines()):
                s = json.loads(line).get('response', {}).get('result', {}).get('structuredContent', {})
                if s.get('elements'):
                    return s
            raise RuntimeError('No AX snapshot')
        js("var app = await cua.getApp('libreoffice-writer');")
        attention = snapshot().get('attention')
        if attention:
            js('var dialog = await cua.getApp(' + json.dumps(attention['target']) + "); await dialog.pressKey('Escape'); await app.getAXState();")
        if case.startswith('dialog'):
            js("await app.pressKey('Ctrl+h'); var replace=await app.getDialog({title:'Find and Replace',timeout_ms:5000});")
            assert snapshot()['windowTitle']=='Find and Replace'
        else:
            js("await app.pressKey('Ctrl+h'); await app.getAXState();")
            js("await app.waitFor({dialog_title:'Find and Replace',timeout_ms:5000});")
            attention=snapshot().get('attention');assert attention and attention['title']=='Find and Replace'
            js('var replace=await cua.getApp('+json.dumps(attention['target'])+');')
        (d/'dialog-window.json').write_text(json.dumps(snapshot()['window']))
        subprocess.run([str(root/'testing/runtime-result/bin/python3'),str(here/'inspect_ax_relations.py'),str(d/'dialog-window.json'),str(d/'relations.json')],env=env,check=True,timeout=20)
        if case.startswith(('fill','dialog')):
            js("await replace.fillForm({fields:[{name:'Find:',value:'draft'},{name:'Replace:',value:'final'}],submit:{name:'Replace All'}});")
            close=next(e for e in snapshot()['elements'] if e.get('name')=='Close' and e.get('controlType')=='button')
            js(f"await replace.click({close['index']}); await app.pressKey('Ctrl+s'); await app.getAXState();")
            time.sleep(.3)
            grade=odf.inspect(doc,'writer',task['check']);(d/'grade.json').write_text(json.dumps(grade));assert grade['passed'],grade
        assert source_hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        results.append({'case':case,'refocus':monitor.trigger.is_set(),'steps':steps})
        print(json.dumps(results[-1]),flush=True)
        server.stdin.close()
        server.wait(timeout=10)
        stop()
        server = None
        owned = None
        for _ in range(100):
            if not any(w['class'] in classes for w in ctl('clients')):
                break
            time.sleep(.05)
finally:
    stop()
    subprocess.run(['hyprctl', 'eval', 'hl.window_rule({name="hypr-use-writer-label-probe",match={class="^(libreoffice.*|soffice)$"}}):set_enabled(false)'], capture_output=True)
    monitor.close()
    (out / 'results.json').write_text(json.dumps({'cases': results, 'refocus': monitor.violations}, indent=2))
    (out / 'observation-results.json').write_text(json.dumps(observation_results, indent=2))
