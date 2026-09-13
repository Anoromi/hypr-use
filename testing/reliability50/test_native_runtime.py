import hashlib,json,tempfile,unittest
from pathlib import Path
from native_runtime import native_runtime
class NativeProvenance(unittest.TestCase):
 def test_binary_and_loaded_metadata_must_match_record(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);session=root/'testing/live-session';session.mkdir(parents=True);binary=root/'plugin.so';binary.write_bytes(b'fixture')
   plugin={'name':'hypr-agent-portal','handle':'one'};version={'commit':'test'}
   (session/'active-plugin.json').write_text(json.dumps({'path':str(binary),'sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'plugins':[plugin.copy()],'hyprland':version}))
   def run(args,**kw):return json.dumps([plugin] if args[1]=='plugins' else version)
   self.assertEqual(native_runtime(root,run)['path'],str(binary))
   plugin['handle']='two'
   with self.assertRaisesRegex(RuntimeError,'differs'):native_runtime(root,run)
   plugin['handle']='one';binary.write_bytes(b'changed')
   with self.assertRaisesRegex(RuntimeError,'binary changed'):native_runtime(root,run)
if __name__=='__main__':unittest.main()
