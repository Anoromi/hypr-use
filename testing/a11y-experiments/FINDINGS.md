# Accessibility action experiments

Implemented a dedicated explicit AT-SPI click path in the local portal MCP server. It accepts integer element IDs, rebuilds and rematches the snapshot before dispatch, and activates the accessibility action without requiring pointer coordinates inside a screenshot. Exact process lifetime and top-level root checks remain in the mutation subprocess. Ambiguous rematches still fail.

The old path calculated a visible pointer position before attempting semantic activation. That rejected accessible menu entries outside the capture and unnecessarily involved pointer/related-window focus machinery. The new explicit path does not invoke that machinery. The response distinguishes accepted dispatch from verified application effect.

## Controlled results

- GTK fixture: three button activations incremented an application-owned counter exactly three times. The second activation followed a window change from tiled to floating and a resize without the caller refreshing its element ID.
- GTK fixture: opening the format menu and selecting ODF changed the application-owned selected format. Five useful semantic actions out of five in the final controlled sequence.
- Real Calc with a private profile: welcome-dialog navigation and dismissal succeeded. Save As format opened, changed ODF to CSV, reopened, and changed CSV back to ODF, all through explicit AT-SPI. Returned selected-format values verified the changes.
- The ODF item in Calc was at y=-105 in screenshot coordinates. The old screenshot-bound check would reject it. Semantic activation succeeded and the closed combo displayed ODF Spreadsheet (.ods).
- 18 regression scripts passed, including new refresh/numeric-ID/off-capture/ambiguous-rematch tests and updated schema smoke coverage.

These tests ran in a separate headless Cage/Hyprland session with a separate D-Bus accessibility registry. No test windows were opened on the user's desktop. The setup initially needed a manually launched private accessibility registry, and Calc needed the GTK3 backend and its own profile.

This is not a measured improvement from 3/7 to a new full-benchmark success rate: the controlled scenarios differ. A fresh autonomous spreadsheet run is still needed to measure that. Automatic/pointer click paths and broader launch-focus problems are not fixed. Refreshing before every explicit AT-SPI click adds observation cost. These experiments verify menu selection, not a newly saved demographics workbook.

Files: summary.json, results.json, wire.json, calc-wire.jsonl, regression-results.json. The experiment scripts live one directory above this folder.
