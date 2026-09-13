import contextlib,io,tempfile,unittest
from pathlib import Path
from phase_options import prepare_phase

class Freshness(unittest.TestCase):
 def test_existing_results_require_explicit_resume(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);phase,selected,out,resume=prepare_phase(['new','task'],root,['task'])
   self.assertEqual(selected,{'task'});self.assertFalse(resume)
   (out/'manifest.json').write_text('{}');(out/'result').write_text('original')
   with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):prepare_phase(['new','task'],root,['task'])
   self.assertEqual((out/'result').read_text(),'original')
   self.assertTrue(prepare_phase(['new','--resume'],root,['task'])[3])
 def test_bad_ids_paths_and_missing_resume_do_not_create_phases(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for args in [['fresh','typo'],['../escape'],['missing','--resume']]:
    with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):prepare_phase(args,root,['task'])
   self.assertEqual(list(root.iterdir()),[])
if __name__=='__main__':unittest.main()
