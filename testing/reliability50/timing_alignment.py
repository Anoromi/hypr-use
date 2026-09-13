"""Match recorded agent calls to wire requests before attributing time."""
def aligned_calls(calls, wire):
    if len(calls) != len(wire):
        return False
    for call, record in zip(calls, wire):
        params = record.get("request", {}).get("params", {})
        if call.get("tool") != params.get("name") or call.get("arguments") != params.get("arguments"):
            return False
    return True
