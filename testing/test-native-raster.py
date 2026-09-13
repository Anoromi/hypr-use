import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'mcp/unified'))
from raster import install
cli=SimpleNamespace();assert install(cli)
resize=cli.resize_rgba_bilinear
# Opaque and transparent uniform images preserve their color/alpha.
for pixel in [bytes([13,44,91,255]),bytes([0,0,0,0]),bytes([50,100,150,128])]:
 for dims in [(9,7,3,2),(3,2,9,7)]:
  w,h,dw,dh=dims;out=resize(pixel*(w*h),w,h,dw,dh)
  assert len(out)==dw*dh*4
  assert all(abs(a-b)<=1 for a,b in zip(out,pixel*(dw*dh))), (pixel,dims)
# Left/right colors must not swap or change image coordinates.
out=resize((bytes([255,0,0,255])*4+bytes([0,0,255,255])*4)*4,8,4,4,2)
assert out[:4]==bytes([255,0,0,255]) and out[12:16]==bytes([0,0,255,255])
for args in [(b'',1,1,1,1),(b'',0,1,1,1)]:
 try:resize(*args)
 except ValueError:pass
 else:raise AssertionError('Invalid buffer accepted')
print('Native RGBA resize preserves dimensions, orientation, color and alpha.')
