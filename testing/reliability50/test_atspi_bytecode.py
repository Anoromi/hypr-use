"""Cached loading retains source freshness, fallback, and one-process-per-scan."""
import importlib.util,json,os,py_compile,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[2]
source=root/'vendor/hypr-agent-portal-0.56.2/mcp/hypr-agent-portal-mcp.py'
spec=importlib.util.spec_from_file_location('portal_bytecode_test',source);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class BytecodeTests(unittest.TestCase):
 def test_explicit_disable_uses_original_script(self):
  with patch.dict(os.environ,{'HYPR_USE_AX_BYTECODE':'0'}):
   self.assertEqual(b.atspi_child_command('--atspi-probe'),[sys.executable,str(source),'--atspi-probe'])
 def test_unwritable_cache_falls_back_once(self):
  with patch.dict(os.environ,{'HYPR_USE_AX_BYTECODE':'1'}),patch.object(b,'ATSPI_BYTECODE_READY',None),patch.object(py_compile,'compile',side_effect=PermissionError('read only')) as compile:
   for _ in range(2):self.assertEqual(b.atspi_child_command('--atspi-probe')[1],str(source))
   self.assertEqual(compile.call_count,1)
 def test_same_size_same_timestamp_edit_invalidates_checked_hash(self):
  with tempfile.TemporaryDirectory(prefix='hypr-use-bytecode-') as tmp:
   d=Path(tmp);runner=d/'atspi_child_runner.py';runner.write_bytes(source.with_name(runner.name).read_bytes())
   module=d/source.name
   code='import json,os,sys\nATSPI_CHILD_MODES={"--atspi-probe"}\nVERSION=1\ndef atspi_child_main(mode):\n print(json.dumps({"version":VERSION,"pid":os.getpid(),"payload":json.load(sys.stdin)}));return 0\n'
   module.write_text(code);stamp=module.stat().st_mtime_ns
   cache=py_compile.compile(str(module),doraise=True,invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH)
   self.assertEqual(int.from_bytes(Path(cache).read_bytes()[4:8],'little'),3)
   def run():return json.loads(subprocess.check_output([sys.executable,str(runner),'--atspi-probe'],input='{"request":42}',text=True))
   first=run();module.write_text(code.replace('VERSION=1','VERSION=2'));os.utime(module,ns=(stamp,stamp));second=run()
   self.assertEqual((first['version'],second['version']),(1,2));self.assertEqual(second['payload'],{'request':42});self.assertNotEqual(first['pid'],second['pid'])
if __name__=='__main__':unittest.main()
