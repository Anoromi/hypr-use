import importlib.util
import types
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('timing',Path(__file__).with_name('portal-timing.py'))
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)

class TimingTests(unittest.TestCase):
    def test_nested_and_failure_spans(self):
        m=types.SimpleNamespace()
        def keyboard():
            m.time.sleep(.001)
            raise ValueError('test')
        m.keyboard=keyboard
        def type_text():
            try:m.keyboard()
            except ValueError:pass
        m.type_text=type_text
        def handle(request):
            if request['method']=='tools/call':m.type_text()
            return {'result':{'content':[]}}
        m.handle=handle
        t.install(m);t.install(m)
        result=m.handle({'method':'tools/call'})['result']['_meta']['hypr-use/timing']
        spans=result['spans']
        self.assertEqual([s['stage'] for s in spans],['type_text','keyboard','sleep'])
        self.assertEqual([s['parent'] for s in spans],[None,0,1])
        self.assertTrue(spans[1]['failed'])
        self.assertAlmostEqual(sum(s['self_ms'] for s in spans)+result['unattributed_ms'],result['total_ms'])
        self.assertIsNone(t._active.get())
        self.assertNotIn('_meta',m.handle({'method':'initialize'})['result'])

if __name__=='__main__':unittest.main()
