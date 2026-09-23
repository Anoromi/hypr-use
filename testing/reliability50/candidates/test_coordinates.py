import unittest
from coordinate_space import document_scale,normalize
class Coordinates(unittest.TestCase):
 def test_recorded_chromium_viewport(self):
  root=dict(x=0,y=0,width=1757,height=1119);doc=dict(x=0,y=139,width=2812,height=1652)
  s=document_scale(doc,root);self.assertAlmostEqual(s,1.6,places=2)
  frame=normalize(dict(x=848,y=353,width=402,height=59),s)
  self.assertAlmostEqual(frame['x'],530,delta=1);self.assertAlmostEqual(frame['y'],220.6,delta=1)
 def test_matching_logical_coordinates(self):
  self.assertIsNone(document_scale(dict(x=0,y=87,width=1757,height=1032),dict(x=0,y=0,width=1757,height=1119)))
 def test_scroll_content_is_not_a_scale(self):
  self.assertIsNone(document_scale(dict(x=0,y=87,width=2812,height=8000),dict(x=0,y=0,width=1757,height=1119)))
 def test_horizontal_overflow_is_not_a_scale(self):
  self.assertIsNone(document_scale(dict(x=0,y=87,width=2812,height=1032),dict(x=0,y=0,width=1757,height=1119)))
 def test_global_origin_not_guessed(self):
  self.assertIsNone(document_scale(dict(x=64,y=144,width=2812,height=1652),dict(x=40,y=3,width=1757,height=1119)))
if __name__=='__main__':unittest.main()
