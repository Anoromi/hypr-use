"""Optional server instrumentation. Records durations, never text or screenshots."""
import contextvars
import functools
import time

_active = contextvars.ContextVar('portal_timing', default=None)


def measured(label, fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        state = _active.get()
        if state is None:
            return fn(*args, **kwargs)
        start = time.perf_counter_ns()
        span = {'stage': label, 'parent': state['stack'][-1] if state['stack'] else None,
                'start_ms': (start-state['start'])/1e6}
        if label == 'call_ctl' and args and args[0]:
            span['verb'] = str(args[0][0])
        if label == 'control_request' and args:
            span['verb'] = str(args[0]).split(' ', 1)[0]
        index = len(state['spans'])
        state['spans'].append(span)
        state['stack'].append(index)
        try:
            return fn(*args, **kwargs)
        except BaseException:
            span['failed'] = True
            raise
        finally:
            span['duration_ms'] = (time.perf_counter_ns()-start)/1e6
            state['stack'].pop()
    return wrapped


def install(module):
    if getattr(module, '_timing_installed', False):
        return
    module._timing_installed = True
    names = ['current_snapshot', 'refresh_snapshot_geometry', 'resolve_hypr_window',
             'control_overlay', 'prepare_grid_bulk_paste', 'type_text', 'type_with_keys',
             'keyboard', 'call_ctl', 'snapshot_after_action', 'build_app_snapshot',
             'related_windows_for', 'screenshot_for_window', 'atspi_snapshot_isolated',
             'global_menu_for_window', 'attach_active_related_preview', 'mcp_snapshot_result',
             'build_security_request', 'audit_security_call', 'control_request',
             'begin_related_action_session', 'finish_related_action_session']
    for name in names:
        if hasattr(module, name):
            setattr(module, name, measured(name, getattr(module, name)))
    # Replace only this module's time reference, never the process-wide time module.
    class TimedTime:
        def __getattr__(self, name):
            return getattr(time, name)
        sleep = staticmethod(measured('sleep', time.sleep))
    module.time = TimedTime()
    original = module.handle

    @functools.wraps(original)
    def handle(request):
        if request.get('method') != 'tools/call' or _active.get() is not None:
            return original(request)
        state = {'start': time.perf_counter_ns(), 'spans': [], 'stack': []}
        token = _active.set(state)
        try:
            result = original(request)
            elapsed = (time.perf_counter_ns()-state['start'])/1e6
            spans = state['spans']
            for span in spans:
                span['self_ms'] = span['duration_ms']
            for span in spans:
                if span['parent'] is not None:
                    spans[span['parent']]['self_ms'] -= span['duration_ms']
            timing = {'total_ms': elapsed,
                      'unattributed_ms': elapsed-sum(s['duration_ms'] for s in spans if s['parent'] is None),
                      'spans': spans,
                      'scope': 'Server handle only; excludes final JSON serialization and transport. Nested durations overlap; use self_ms for totals.'}
            if isinstance(result, dict) and isinstance(result.get('result'), dict):
                result['result'].setdefault('_meta', {})['hypr-use/timing'] = timing
            return result
        finally:
            _active.reset(token)
    module.handle = handle
