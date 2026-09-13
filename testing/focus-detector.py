"""Detect transitions into agent-owned windows, not unrelated user switches."""
class FocusDetector:
    def __init__(self, active):
        self.active = active
        self.targets = set()
        self.reported = False

    def register(self, address):
        self.targets.add(address)
        return self.observe(self.active)

    def observe(self, address):
        self.active = address
        if address not in self.targets:
            self.reported = False
            return False
        if self.reported:
            return False
        self.reported = True
        return True
