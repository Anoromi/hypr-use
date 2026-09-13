import base64
import os
import struct
import unittest
import zlib
from unittest.mock import patch
from image_transport import optimize_images

def png(w,h,transparent=False):
    def chunk(t,b):
        return struct.pack('!I',len(b))+t+b+struct.pack('!I',zlib.crc32(t+b)&0xffffffff)
    data=bytearray(os.urandom(w*h*4))
    data[3::4]=bytes([0 if transparent else 255])*(w*h)
    raw=b''.join(b'\0'+data[y*w*4:(y+1)*w*4] for y in range(h))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')

def result(data):return {'content':[{'type':'image','mimeType':'image/png','data':base64.b64encode(data).decode()}]}

class Transport(unittest.TestCase):
    def test_opaque_geometry_and_reduction(self):
        r=result(png(400,300));original=r['content'][0]['data'];optimize_images(r)
        self.assertEqual(r['content'][0]['mimeType'],'image/jpeg')
        self.assertLess(len(r['content'][0]['data']),len(original))
        from gi.repository import GdkPixbuf
        loader=GdkPixbuf.PixbufLoader.new();loader.write(base64.b64decode(r['content'][0]['data']));loader.close()
        self.assertEqual((loader.get_pixbuf().get_width(),loader.get_pixbuf().get_height()),(400,300))
    def test_transparency_is_lossless(self):
        r=result(png(400,300,True));original=r['content'][0].copy();optimize_images(r);self.assertEqual(r['content'][0],original)
    def test_lossless_override(self):
        r=result(png(400,300));original=r['content'][0].copy()
        with patch.dict(os.environ,{'HYPR_USE_IMAGE_FORMAT':'png'}):optimize_images(r)
        self.assertEqual(r['content'][0],original)
    def test_small_png_unchanged(self):
        r=result(png(10,10));original=r['content'][0].copy();optimize_images(r);self.assertEqual(r['content'][0],original)
if __name__=='__main__':unittest.main()
