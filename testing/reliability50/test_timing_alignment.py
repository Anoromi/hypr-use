import unittest
from timing_alignment import aligned_calls

class AlignmentTests(unittest.TestCase):
    def test_exact_mixed_calls_match(self):
        calls=[{"tool":"js","arguments":{"code":"await app.getAXState();"}},{"tool":"fill_form","arguments":{"app":"test","fields":[{"name":"Name","value":"Ada"}]}}]
        wire=[{"request":{"params":{"name":c["tool"],"arguments":c["arguments"]}}} for c in calls]
        self.assertTrue(aligned_calls(calls,wire))
        self.assertFalse(aligned_calls(calls,wire[:-1]))
    def test_different_non_js_tools_do_not_match_as_missing_code(self):
        self.assertFalse(aligned_calls([{"tool":"navigate","arguments":{"app":"test"}}],[{"request":{"params":{"name":"wait_for","arguments":{"app":"test"}}}}]))
    def test_same_tool_different_arguments_do_not_match(self):
        self.assertFalse(aligned_calls([{"tool":"wait_for","arguments":{"text":"Ready"}}],[{"request":{"params":{"name":"wait_for","arguments":{"text":"Saved"}}}}]))

if __name__=="__main__":unittest.main()
