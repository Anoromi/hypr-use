import unittest
from types import SimpleNamespace

from runtime_fixes import install


class RuntimeFixTests(unittest.TestCase):
    def test_uses_window_coordinates_when_hidden_screen_origin_is_broken(self):
        screen = {"x": 0.0, "y": 0.0, "width": 80.0, "height": 20.0}
        rect = SimpleNamespace(x=30, y=76, width=80, height=20)
        backend = SimpleNamespace(
            atspi_extents=lambda _node: screen,
            atspi_safe=lambda call: call(),
            _ATSPI=SimpleNamespace(Component=SimpleNamespace(get_extents=lambda _component, _space: rect), CoordType=SimpleNamespace(WINDOW=1)),
            resolve_hypr_window=lambda app: {"original": app},
            parse_target=lambda app: SimpleNamespace(selector=app, qualified=False),
            normalize=lambda value: str(value or "").lower(),
            list_hypr_windows=lambda: [],
            process_start_time=lambda _pid: "0",
            window_geometry=lambda _window: {"width": 1, "height": 1},
            atspi_child_command=lambda mode: ["old", mode],
        )
        install(backend)
        node = SimpleNamespace(get_component_iface=lambda: object())
        self.assertEqual(backend.atspi_extents(node), {"x": 30.0, "y": 76.0, "width": 80.0, "height": 20.0})
        self.assertTrue(backend.atspi_child_command("--atspi-snapshot")[1].endswith("atspi_child.py"))

    def test_ambiguous_exact_class_uses_newest_process(self):
        windows = [
            {"class": "Editor", "pid": 1, "focusHistoryID": 0, "size": [100, 100]},
            {"class": "Editor", "pid": 2, "focusHistoryID": 9, "size": [100, 100]},
        ]
        backend = SimpleNamespace(
            atspi_extents=lambda _node: None,
            atspi_safe=lambda call: call(),
            _ATSPI=SimpleNamespace(Component=SimpleNamespace(get_extents=lambda *_args: None), CoordType=SimpleNamespace(WINDOW=1)),
            resolve_hypr_window=lambda app: {"original": app},
            parse_target=lambda app: SimpleNamespace(selector=app, qualified=False),
            normalize=lambda value: str(value or "").lower(),
            list_hypr_windows=lambda: windows,
            process_start_time=lambda pid: {1: "10", 2: "20"}[pid],
            window_geometry=lambda window: {"width": window["size"][0], "height": window["size"][1]},
        )
        install(backend)
        self.assertEqual(backend.resolve_hypr_window("editor")["pid"], 2)

    def test_combo_descendant_click_uses_pointer_to_establish_key_focus(self):
        seen = []
        elements = [
            {"index": 3, "runtimeId": [0, 1], "controlType": "combo box"},
            {"index": 4, "runtimeId": [0, 1, 0], "controlType": "toggle button"},
            {"index": 5, "runtimeId": [0, 2], "controlType": "toggle button"},
        ]
        backend = SimpleNamespace(
            atspi_extents=lambda _node: None,
            atspi_safe=lambda call: call(),
            _ATSPI=SimpleNamespace(Component=SimpleNamespace(get_extents=lambda *_args: None), CoordType=SimpleNamespace(WINDOW=1)),
            resolve_hypr_window=lambda app: {"original": app},
            parse_target=lambda app: SimpleNamespace(selector=app, qualified=True),
            normalize=lambda value: str(value or "").lower(),
            list_hypr_windows=lambda: [],
            process_start_time=lambda _pid: "0",
            window_geometry=lambda _window: {"width": 1, "height": 1},
            semantic_click=lambda args: seen.append(args) or {},
            SEMANTIC_TOOLS={},
            element_click_mode=lambda args: args.get("element_click_mode", "pointer"),
            SNAPSHOTS={"bound": {"elements": elements}},
            lookup_element=lambda snapshot, index: next(item for item in snapshot["elements"] if item["index"] == int(index)),
            element_role=lambda element: element["controlType"],
        )
        install(backend)
        backend.SEMANTIC_TOOLS["click"]({"app": "bound", "element_index": "4", "element_click_mode": "auto"})
        backend.SEMANTIC_TOOLS["click"]({"app": "bound", "element_index": "5", "element_click_mode": "auto"})
        self.assertEqual(seen[0]["element_click_mode"], "pointer")
        self.assertEqual(seen[1]["element_click_mode"], "auto")

if __name__ == "__main__":
    unittest.main()
