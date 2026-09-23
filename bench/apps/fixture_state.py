from __future__ import annotations


def initialize_target_pair(state: dict) -> None:
    state.update(target_complete=False, distractor_complete=False, distractor_untouched=True)


def complete_target_window(state: dict, role: str) -> None:
    if role == "target":
        state["target_complete"] = True
    elif role == "distractor":
        state["distractor_complete"] = True
        state["distractor_untouched"] = False
    else:
        raise ValueError(f"unknown target-pair role: {role}")


def submit_quick_entry(state: dict, value: str) -> str:
    state["quick_entry"] = value
    state["quick_entry_submitted"] = True
    return f"Quick entry submitted: {value}"
