# Oracle run audit

The recorded `oracle-all90` run completed 90 tasks and passed 30. It predates the fixes below,
so its 30/90 score is historical evidence, not the expected score of the current catalog.

Failure classification from the saved result files:

| Count | Classification | Current status |
|---:|---|---|
| 13 | Dialog actions incorrectly searched the root window AX tree | Fixed with `get_dialog` and `dialog_click` |
| 7 | GTK dropdown exposed no AX node named `Country` | Oracle now operates the real dropdown by its displayed value and keyboard; requires live rerun |
| 6 | Coordinate click oracle referenced an unset `idx` | Fixed with explicit coordinate handling |
| 1 | Rapid-action benchmark inherited a 45-second call timeout | Fixed with a 180-second bounded timeout |
| 28 | State mismatch after an accepted action, mostly editable text | Retry and re-observation added; requires a live rerun |
| 3 | Virtualized rows remained absent after scrolling | Unresolved tool/fixture interaction |
| 2 | App registry or workspace lifecycle failure | Unresolved environment/tool lifecycle |

The two cross-application T5 long-horizon tasks contain 27 oracle actions across list, form, and
editor fixtures. Graders verify exact submitted field values, saved editor content, selected rows,
and explicit observation evidence. Agent final-answer grading excludes prompt and tool output.
