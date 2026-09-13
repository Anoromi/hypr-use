# Baseline observations to investigate

The official comparison uses gpt-6-astra, high reasoning, fresh codex exec per task. Earlier Sol directories are setup attempts and excluded.

Observed in the first 12 Astra tasks:
- Fixture tasks 1–5, 7–8 independently passed; task 6 failed. No target foreground events detected.
- Task 6 selected text in Note, but typeText inserted DELTA in Name. select_node changes the Text selection without focusing its widget, while typeText sends window-directed keys. Entry click is forced to AT-SPI activate, which may submit instead of focusing.
- getScreenshot emitted a black fixture image in task 3. Native renderWindow is called with standalone=false. Hyprland renderWindow multiplies opacity by hidden-workspace alpha; standalone=true forces full opacity. Verify against actual current source and pixels before claiming a fix.
- Coordinate inference: task 6 client and screenshot origin (-840,3), AX root origin (0,0), widths both ~1316. atspi_bounds_are_global currently treats any overlapping rectangles as proof of global coordinates, producing AX frames around (840,-3) inside the screenshot. This appears wrong for local Wayland roots.
- Zen AX output hits 500 records with offscreen sidebar tabs and omits document content. atspi_node_is_currently_visible returns true for essentially any nonempty bounds. Consider viewport filtering while preserving structural nodes and selected tabs, plus bounded traversal.
- Several 4-operation JS batches hit the default 30s limit. The error says 'Execution cancelled', causing agents to interpret timeout as cancellation and stop. Completed operation timing is lost from the outer result on timeout, though completed portal responses remain recorded.
- getAXState uses the same full screenshot+AX build as combined observation. Every action builds and returns an automatic post-action snapshot, discarded by the facade. The explicit observation immediately builds another.
- Among measured call_ctl time early in baseline, screenshot capture dominates, then sessions/policy and keyboard commands. Root-level call_ctl instrumentation lacks verb labels; do not pretend those calls can be separated exactly from existing logs.
- Each guarded action finishes with up to six sync/check cycles and five 80ms sleeps. Preserve focus protection; consider a persistent guarded session with explicit lifecycle cleanup instead of removing protection.
- Calc private welcome window class is soffice, while task confinement is libreoffice-calc. This is a benchmark setup limitation to report and correct consistently, rather than misattribute as model failure.

Do not alter an implementation while its phase is running. Backend/plugin source snapshots are in astra-baseline. Independent per-task fixture assertions only cover requested state keys, not all possible collateral state changes. Later Calc tasks depend on earlier tasks. Web and intermediate Calc outputs are not independently verified yet.

Follow-up: Original Calc setup attempts 18–20 were excluded due to scope misconfiguration; corrected original-implementation runs live in astra-baseline-calc. Use tasks 01–17 from astra-baseline plus 18–24 from astra-baseline-calc as the valid 24-task baseline. Pixel inspection of fixture task03 and Calc tasks19/20 found one-color PNGs with mean RGB=0 and alpha mean=0. Files image-analysis.json record the results. Calc task18 passed AX review after welcome dismissal and import recovery, taking178s. Amazon task16 passed parent screenshot review. Review files distinguish those from mechanical fixture assertions.
