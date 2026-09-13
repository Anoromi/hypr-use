"""AX reads must advance hidden clients; failed preparation must not publish stale AX."""
import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp/unified'))
from observations import Observations

class FramePreparation(unittest.TestCase):
 def make_backend(self,fail=False):
  calls=[]
  def ctl(args):
   calls.append(('prepare',args))
   if fail:raise RuntimeError('native guard rejected preparation')
  b=SimpleNamespace(snapshot_after_action=lambda *a:None,
   atspi_snapshot_isolated=lambda *a:calls.append(('scan',a)) or {'status':'ok'},
   window_selector=lambda w:w['target'],call_ctl=ctl,
   time=SimpleNamespace(sleep=lambda seconds:calls.append(('wait',seconds))),
   SEMANTIC_TOOLS={n:lambda a:None for n in ['click','scroll','set_value','select_text','perform_secondary_action']},
   ensure_global_menu_backends=lambda:None,dbus_services_for_pid=lambda pid:[],dbus_tree_paths=lambda owner:[])
  Observations(b)
  return b,calls
 def test_ax_only_prepares_bound_target_before_scan(self):
  b,c=self.make_backend();b.atspi_snapshot_isolated({'target':'address:0x123@pid=7@start=9'},{'captureKind':'geometry-only'})
  self.assertEqual([x[0] for x in c],['prepare','wait','scan'])
  self.assertEqual(c[0][1],['prepare-frame','--target','address:0x123@pid=7@start=9'])
 def test_captured_observation_does_not_prepare_twice(self):
  b,c=self.make_backend();b.atspi_snapshot_isolated({}, {'captureKind':'native'})
  self.assertEqual([x[0] for x in c],['scan'])
 def test_guard_failure_prevents_stale_scan(self):
  b,c=self.make_backend(True)
  with self.assertRaisesRegex(RuntimeError,'native guard'):b.atspi_snapshot_isolated({'target':'bound'},{'captureKind':'geometry-only'})
  self.assertEqual([x[0] for x in c],['prepare'])

if __name__=='__main__':unittest.main()
