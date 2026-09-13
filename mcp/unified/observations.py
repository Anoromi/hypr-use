"""Lazy observations and bounded discovery caches for the unified adapter."""
import copy
import os
import time


class Observations:
    def __init__(self, backend):
        self.b = backend
        self.published = {}
        self.install()

    def publish(self, query, snapshot):
        if not snapshot or snapshot.get('observationDeferred'):
            return
        for key in (query, snapshot.get('target')):
            if key:
                self.published[self.b.normalize(key)] = snapshot

    def rematch(self, old, fresh):
        b = self.b
        candidates = [e for e in fresh.get('elements', [])
                      if b.element_role(e) == b.element_role(old)
                      and e.get('source') == old.get('source')
                      and b.normalize(e.get('name')) == b.normalize(old.get('name'))]
        exact = [e for e in candidates if old.get('runtimeId') is not None
                 and e.get('runtimeId') == old.get('runtimeId')]
        if len(exact) == 1:
            return exact[0]
        named = [e for e in candidates if old.get('name') or old.get('automationId')]
        if old.get('automationId'):
            named = [e for e in named if e.get('automationId') == old['automationId']]
        if len(named) == 1:
            return named[0]
        raise RuntimeError('Element changed or became ambiguous; call getAXState and choose it again')

    def install(self):
        b = self.b
        # The unified JS facade exposes AT-SPI elements, not the portal's
        # separate globalMenu collection or activate_menu_item operation.
        # Discovering that unused collection adds D-Bus work to observations
        # and every indexed action's identity-rematching scan. Visible AX
        # menus remain available. Retain an opt-in for paired diagnostics.
        if os.environ.get('HYPR_USE_GLOBAL_MENU', '0') != '1':
            b.global_menu_for_window = lambda window: {'status': 'not-requested', 'items': []}
        original_after = b.snapshot_after_action
        original_atspi = b.atspi_snapshot_isolated

        def fresh_atspi(window, screenshot):
            # Hidden Wayland windows can retain a closed tab in their AX tree
            # until frame callbacks advance the UI. Screenshots already wake
            # the client; AX-only reads need the same preparation, without pixels.
            if screenshot.get('captureKind') == 'geometry-only':
                b.call_ctl(['prepare-frame', '--target', b.window_selector(window)])
                b.time.sleep(0.12)
            return original_atspi(window, screenshot)

        b.atspi_snapshot_isolated = fresh_atspi

        def after(app, before, action_result=None):
            # Keep a live identity/window-delta check, but no pixels or AX scan.
            try:
                window = b.resolve_hypr_window(b.snapshot_window_query(before, app))
            except Exception as ex:
                if not b.is_app_not_found_error(ex):
                    raise
                return original_after(app, before, action_result)
            state = {**before, 'window': window, 'windowTitle': window.get('title', ''),
                     'elements': [], 'treeLines': [], 'uiHints': {},
                     'screenshotPngBase64': '', 'activeRelatedScreenshotPngBase64': '',
                     'accessibility': {'status': 'deferred'}, 'globalMenu': {},
                     'observationDeferred': True}
            state['relatedWindows'] = b.privacy_filtered_related_windows(b.related_windows_for(before['target']))
            b.merge_last_action(state, before, action_result)
            return state

        b.snapshot_after_action = after
        # Published AX indices remain bound to the last observation delivered
        # to the client, not to an internal scan performed during another action.
        for name in ('click', 'scroll', 'set_value', 'select_text', 'perform_secondary_action'):
            fn = b.SEMANTIC_TOOLS[name]

            def invoke(args, fn=fn):
                index = args.get('element_index')
                if index is not None:
                    app = str(args['app'])
                    previous = self.published.get(b.normalize(app))
                    if previous is None:
                        raise RuntimeError('Indexed input requires getAXState first')
                    old = b.lookup_element(previous, str(index))
                    fresh = b.build_app_snapshot(b.snapshot_window_query(previous, app))
                    selected = self.rematch(old, fresh)
                    args = {**args, 'element_index': str(selected['index'])}
                return fn(args)

            b.SEMANTIC_TOOLS[name] = invoke

        def cached(fn, seconds, key_fn):
            values = {}

            def get(*args):
                key = key_fn(*args)
                entry = values.get(key)
                if entry is not None and time.monotonic() - entry[0] < seconds:
                    return copy.deepcopy(entry[1])
                value = fn(*args)
                if len(values) > 128:
                    values.clear()
                values[key] = (time.monotonic(), copy.deepcopy(value))
                return value

            return get

        # Cache discovery only; menu item state is still read on each AX scan.
        b.ensure_global_menu_backends = cached(b.ensure_global_menu_backends, 60, lambda: ())
        b.dbus_services_for_pid = cached(b.dbus_services_for_pid, 2, lambda pid: (pid, b.process_start_time(pid)))
        b.dbus_tree_paths = cached(b.dbus_tree_paths, 2, lambda owner: owner)
