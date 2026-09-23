import unittest
from empty_cells import confirmed_empty_text_cell,retain_cell
class EmptyCells(unittest.TestCase):
 def test_unknown_is_not_empty(self):
  self.assertFalse(confirmed_empty_text_cell(True,None));self.assertFalse(confirmed_empty_text_cell(False,0))
 def test_actual_zero_is_kept(self):
  self.assertFalse(confirmed_empty_text_cell(True,1))
  self.assertTrue(retain_cell(empty=False,selected=False,focused=False,empty_seen=1000))
 def test_selected_blank_is_kept(self):
  self.assertTrue(retain_cell(empty=True,selected=True,focused=False,empty_seen=1000))
  self.assertTrue(retain_cell(empty=True,selected=False,focused=True,empty_seen=1000))
 def test_sampling_is_bounded(self):
  retained=sum(retain_cell(empty=True,selected=False,focused=False,empty_seen=i) for i in range(500))
  self.assertEqual(retained,12)
if __name__=='__main__':unittest.main()
