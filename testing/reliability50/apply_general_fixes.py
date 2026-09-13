"""Apply shared fixes only after the frozen baseline has finished."""
from pathlib import Path
import shutil,sys
root=Path(__file__).resolve().parents[2]
v=root/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py';f=root/'mcp/unified/facade.mjs'
a=v.read_text();b=f.read_text()
def replace(s,old,new):
 assert s.count(old)==1,old[:100]
 return s.replace(old,new,1)
a=replace(a,'def atspi_action_names(node: Any) -> list[str]:\n    names = []','def atspi_action_names(node: Any) -> list[str]:\n    if not bool(atspi_safe(node.is_action, False)):\n        return []\n    names = []')
a=replace(a,'def atspi_numeric_value(node: Any) -> str:\n    value_iface', 'def atspi_numeric_value(node: Any) -> str:\n    if not bool(atspi_safe(node.is_value, False)):\n        return ""\n    value_iface')
helper='''def atspi_confirmed_empty_text(node: Any) -> bool:
    if not bool(atspi_safe(node.is_text, False)):
        return False
    iface = atspi_safe(node.get_text_iface)
    return iface is not None and atspi_safe(lambda: _ATSPI.Text.get_character_count(iface), None) == 0


def atspi_document_coordinate_scale(bounds: dict[str, float] | None, root: dict[str, float] | None) -> float | None:
    # Infer only a full-viewport document in local Wayland coordinates. Oversized
    # scroll content, matching logical coordinates and global origins do not qualify.
    if not bounds or not root or root["width"] <= 0 or root["height"] <= 0:
        return None
    if abs(root["x"]) > .01 or abs(root["y"]) > .01 or abs(bounds["x"]) > 2:
        return None
    sx = bounds["width"] / root["width"]
    sy = (bounds["y"] + bounds["height"]) / root["height"]
    if not 1.1 <= sx <= 4 or abs(sx - sy) > .01 * max(sx, sy):
        return None
    return (sx + sy) / 2


'''
a=replace(a,'def atspi_image_frame(\n',helper+'def atspi_image_frame(\n')
a=replace(a,'"supportsEditableText": bool(atspi_safe(node.is_editable_text, False)) and bool(atspi_safe(node.is_text, False)),','"supportsEditableText": bool(atspi_safe(node.is_editable_text, False)) and bool(atspi_safe(node.is_text, False)),\n        "supportsValue": bool(atspi_safe(node.is_value, False)),')
a=replace(a,'    truncated_reason = ""\n\n    def mark_truncated', '    truncated_reason = ""\n    omitted_empty_cells = 0\n    omitted_grid_ranges = []\n\n    def mark_truncated')
a=replace(a,'def visit(node: Any, depth: int, path: list[int], bounds_hint: dict[str, float] | None = None, document_allowed: bool = False) -> None:', 'def visit(node: Any, depth: int, path: list[int], bounds_hint: dict[str, float] | None = None, document_allowed: bool = False, coordinate_scale: float | None = None) -> None:')
a=replace(a,'        is_document = atspi_role(node) in {"document web", "document frame"}\n', '        is_document = atspi_role(node) in {"document web", "document frame"}\n        if is_document and coordinate_scale is None and not hypr_window.get("xwayland", False):\n            coordinate_scale = atspi_document_coordinate_scale(bounds, atspi_window_bounds)\n        if coordinate_scale is not None and bounds is not None:\n            bounds = {key: value / coordinate_scale for key, value in bounds.items()}\n')
a=replace(a,'        if visit_table_cells(node, depth, path, bounds):', '        if coordinate_scale is None and visit_table_cells(node, depth, path, bounds):')
a=replace(a,'visit(atspi_child_at(node, child_index), depth + 1, path + [child_index], document_allowed=document_allowed or is_document)', 'visit(atspi_child_at(node, child_index), depth + 1, path + [child_index], document_allowed=document_allowed or is_document, coordinate_scale=coordinate_scale)')
a=replace(a,'    def visit_table_cells(node: Any, depth: int, path: list[int], table_bounds: dict[str, float] | None) -> bool:\n', '    def visit_table_cells(node: Any, depth: int, path: list[int], table_bounds: dict[str, float] | None) -> bool:\n        nonlocal omitted_empty_cells\n        empty_retained = 0\n        table_record_index = records[-1]["index"]\n')
a=replace(a,'                row_visible = True\n                empty_cols = 0\n                child_index', '                row_visible = True\n                empty_cols = 0\n                confirmed_empty = atspi_confirmed_empty_text(cell)\n                numeric_value = atspi_numeric_value(cell) if confirmed_empty else None\n                sampleable = confirmed_empty and numeric_value in {"", "0", "0.0"}\n                important = atspi_state_contains(cell, _ATSPI.StateType.SELECTED) or atspi_state_contains(cell, _ATSPI.StateType.FOCUSED)\n                if sampleable and not important and empty_retained >= 12:\n                    omitted_empty_cells += 1\n                    if omitted_grid_ranges and omitted_grid_ranges[-1][:2] == [table_record_index, row] and omitted_grid_ranges[-1][3] == col - 1 and omitted_grid_ranges[-1][4] == numeric_value:\n                        omitted_grid_ranges[-1][3] = col\n                    else:\n                        omitted_grid_ranges.append([table_record_index, row, col, col, numeric_value])\n                    continue\n                if sampleable:\n                    empty_retained += 1\n                child_index')
a=replace(a,'    visit(root, 0, root_path)\n    return records, lines, atspi_window_bounds, truncated_reason', '    visit(root, 0, root_path)\n    if omitted_empty_cells:\n        lines.append(f"Blank-text grid cells summarized: {omitted_empty_cells}; selected/focused cells and an empty-text sample retain individual indices.")\n        for table_index, row, first, last, numeric in omitted_grid_ranges:\n            reported = numeric or "not exposed"\n            lines.append(f"Table {table_index}, row {row + 1}, columns {first + 1}-{last + 1}: accessible text empty; reported AX numeric value {reported}.")\n    return records, lines, atspi_window_bounds, truncated_reason')
a=replace(a,'        actions_segment = " Secondary Actions: "', '        if normalize(role) in {"entry", "text", "password text", "spin button"}:\n            value_segment += " SetValue: " + ("supported" if record.get("supportsEditableText") or record.get("supportsValue") else "unsupported")\n        actions_segment = " Secondary Actions: "')
a=replace(a,'            if mode == "pointer" and element_is_menu_item(element) and element_has_primary_atspi_action(element):\n                mode = "atspi"\n','')
start=a.index('    try:\n        element = best_scroll_element',a.index('def semantic_press_key'))
end=a.index('    info: dict[str, Any] = {}',start)
a=a[:start]+'''    # Keyboard input belongs to the explicitly bound window, not a hit-tested
    # scroll surface. Scroll centers are screenshot-relative, while the native
    # keyboard coordinate option expects global coordinates.
    control_overlay(snapshot, action="key")
'''+a[end:]
a=replace(a,'info = keyboard(str(snapshot["target"]), key, modifiers, x, y)', 'info = keyboard(str(snapshot["target"]), key, modifiers)')
b=replace(b,"element_click_mode:'auto'","element_click_mode:'pointer'")
old="pressKey:async(key)=>{key=string(key,'key').split(' ').map(c=>c.split('+').map(t=>['super','cmd','command'].includes(t.toLowerCase())?(options.commandModifier??'ctrl'):t).join('+')).join(' ');await act('press_key',{key});},"
new="""pressKey:async(key)=>{
        const sequence=string(key,'key').trim().split(/\\s+/);
        if(!sequence[0])throw Error('key must not be empty');
        for(const combination of sequence){
          const key=combination.split('+').map(t=>['super','cmd','command'].includes(t.toLowerCase())?(options.commandModifier??'ctrl'):t).join('+');
          await act('press_key',{key});
        }
      },"""
b=replace(b,old,new)
compile(a,str(v),'exec')
if '--check' in sys.argv:
 print('All patch anchors and Python syntax verified; runtime unchanged.');sys.exit(0)
backup=root/'testing/reliability50/general-fix-backup';backup.mkdir(exist_ok=False)
for path,text in [(v,a),(f,b)]:
 shutil.copy2(path,backup/path.name);path.write_text(text)
print('Applied shared interface, coordinate, grid, click and keyboard fixes. No task identifiers or answers in runtime changes.')
