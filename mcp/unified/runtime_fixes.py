"""Small runtime corrections layered over the pinned portal backend."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _valid_rect(rect: Any) -> dict[str, float] | None:
    if rect is None:
        return None
    try:
        values = {key: float(getattr(rect, key)) for key in ("x", "y", "width", "height")}
    except (AttributeError, TypeError, ValueError):
        return None
    if values["width"] <= 0 or values["height"] <= 0:
        return None
    if any(abs(values[key]) > 100000 for key in values):
        return None
    return values


def install(backend: Any) -> None:
    original_extents = backend.atspi_extents

    def corrected_extents(node: Any) -> dict[str, float] | None:
        screen = original_extents(node)
        if screen is not None and (abs(screen["x"]) > 0.01 or abs(screen["y"]) > 0.01):
            return screen
        component = backend.atspi_safe(node.get_component_iface)
        if component is None:
            return screen
        local = _valid_rect(backend.atspi_safe(
            lambda: backend._ATSPI.Component.get_extents(component, backend._ATSPI.CoordType.WINDOW)
        ))
        # Hidden GTK Wayland windows can preserve width/height in SCREEN space
        # while returning (0,0) for every descendant. WINDOW space retains the
        # real child offset. Keep a genuine shared origin unchanged.
        if local is not None and (screen is None or abs(local["x"]) > 0.01 or abs(local["y"]) > 0.01):
            return local
        return screen

    original_resolve = backend.resolve_hypr_window

    def freshest_exact_window(app: str) -> dict[str, Any]:
        try:
            parsed = backend.parse_target(app)
        except ValueError:
            return original_resolve(app)
        query = backend.normalize(parsed.selector)
        if parsed.qualified or query.startswith("address:") or query.startswith("0x") or query.isdigit():
            return original_resolve(app)
        windows = backend.list_hypr_windows()

        def field(window: dict[str, Any], key: str) -> str:
            return backend.normalize(window.get(key))

        candidates = [window for window in windows if query in {field(window, "class"), field(window, "initialClass")}]
        if not candidates:
            candidates = [window for window in windows if query in {field(window, "title"), field(window, "initialTitle")}]
        if len(candidates) < 2:
            return original_resolve(app)

        def recency(window: dict[str, Any]) -> tuple[int, int, float]:
            try:
                started = int(backend.process_start_time(window.get("pid")) or 0)
            except (TypeError, ValueError):
                started = 0
            focus = window.get("focusHistoryID")
            focus_score = int(focus) if isinstance(focus, int) else 1_000_000
            geometry = backend.window_geometry(window)
            return -started, focus_score, -(geometry["width"] * geometry["height"])

        return sorted(candidates, key=recency)[0]

    backend.atspi_extents = corrected_extents
    backend.resolve_hypr_window = freshest_exact_window
    if hasattr(backend, "atspi_child_command"):
        child = Path(__file__).with_name("atspi_child.py")
        backend.atspi_child_command = lambda mode: [sys.executable, str(child), mode]
    if hasattr(backend, "semantic_click") and hasattr(backend, "SEMANTIC_TOOLS"):
        original_click = backend.semantic_click

        def click_with_native_combo_focus(args: dict[str, Any]) -> dict[str, Any]:
            routed = args
            element_index = args.get("element_index")
            if (backend.element_click_mode(args) == "auto" and element_index is not None
                    and str(args.get("mouse_button") or "left") == "left"
                    and int(args.get("click_count") or 1) == 1):
                snapshot = backend.SNAPSHOTS.get(backend.normalize(args.get("app")))
                if isinstance(snapshot, dict):
                    try:
                        element = backend.lookup_element(snapshot, str(element_index))
                    except RuntimeError:
                        element = None
                    if isinstance(element, dict):
                        path = element.get("runtimeId")
                        ancestors = []
                        if isinstance(path, list):
                            ancestors = [
                                candidate for candidate in snapshot.get("elements") or []
                                if isinstance(candidate, dict)
                                and isinstance(candidate.get("runtimeId"), list)
                                and len(candidate["runtimeId"]) < len(path)
                                and path[:len(candidate["runtimeId"])] == candidate["runtimeId"]
                            ]
                        roles = {backend.element_role(element), *(backend.element_role(item) for item in ancestors)}
                        if "combo box" in roles:
                            routed = {**args, "element_click_mode": "pointer"}
            return original_click(routed)

        backend.semantic_click = click_with_native_combo_focus
        backend.SEMANTIC_TOOLS["click"] = click_with_native_combo_focus
