import importlib.util,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace as NS
from contextlib import ExitStack
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('portal',root/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class Enumeration(unittest.TestCase):
 def test_enumeration_never_asks_unrelated_apps_for_names(self):
  apps=[object(),object()]
  with patch.object(b,'atspi_desktop',return_value=object()),patch.object(b,'atspi_child_count',return_value=2),patch.object(b,'atspi_child_at',side_effect=apps),patch.object(b,'atspi_name',side_effect=AssertionError('Blocked name RPC')):
   self.assertEqual(b.atspi_iter_apps(),apps)
 def test_pid_match_avoids_name_fallback(self):
  app=object();window=object()
  with patch.object(b,'atspi_available',return_value=True),patch.object(b,'atspi_iter_apps',return_value=[app]),patch.object(b,'atspi_pid',return_value=42),patch.object(b,'atspi_name',side_effect=AssertionError('Name RPC')),patch.object(b,'atspi_match_window',return_value=(0,window)):
   self.assertEqual(b.atspi_resolve_window({'pid':42}), (app,0,window))
 def test_empty_name_is_not_a_fallback_match(self):
  with patch.object(b,'atspi_available',return_value=True),patch.object(b,'atspi_iter_apps',return_value=[object()]),patch.object(b,'atspi_pid',return_value=1),patch.object(b,'atspi_name',return_value=''),patch.object(b,'atspi_match_window',side_effect=AssertionError('Empty name matched')):
   self.assertIsNone(b.atspi_resolve_window({'pid':42,'class':'browser','title':'Page'}))
 def test_timeout_preserves_binary_stderr_diagnostics(self):
  failure=subprocess.TimeoutExpired('child',6,stderr=b'stack marker')
  with patch.object(b.subprocess,'run',side_effect=failure),patch.object(b,'atspi_child_env',return_value={}):
   result=b.run_atspi_child('--atspi-snapshot',{},timeout=6)
  self.assertEqual(result['status'],'timeout');self.assertIn('stack marker',result['error'])
if __name__=='__main__':unittest.main()
