"""Offline comparison of the existing screenshot resizer and GdkPixbuf."""
import importlib.machinery
import importlib.util
import json
import time
from pathlib import Path
import gi
gi.require_version('GdkPixbuf','2.0')
from gi.repository import GdkPixbuf, GLib
root=Path(__file__).resolve().parents[2]
loader=importlib.machinery.SourceFileLoader('portal_ctl_resize',str(root/'vendor/hypr-agent-portal-0.56.2/scripts/hypr-agent-portalctl'))
spec=importlib.util.spec_from_loader(loader.name,loader);cli=importlib.util.module_from_spec(spec);loader.exec_module(cli)
def native(src,w,h,dw,dh):
    pix=GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(src),GdkPixbuf.Colorspace.RGB,True,8,w,h,w*4)
    out=pix.scale_simple(dw,dh,GdkPixbuf.InterpType.BILINEAR)
    data=out.get_pixels();stride=out.get_rowstride()
    return b''.join(data[y*stride:y*stride+dw*4] for y in range(dh))
# Opaque ramp and alpha ramp exercise channels and pixel positions.
w,h,dw,dh=1920,1080,1280,720
row=bytes(c for x in range(w) for c in (x%256,(x//8)%256,127,255))
src=row*h
results={}
outputs=[]
for name,fn in [('python',cli.resize_rgba_bilinear),('gdk_pixbuf',native)]:
    start=time.perf_counter();out=fn(src,w,h,dw,dh);elapsed=time.perf_counter()-start
    assert len(out)==dw*dh*4
    outputs.append(out);results[name]={'seconds':elapsed,'bytes':len(out)}
results['max_channel_difference']=max(abs(a-b) for a,b in zip(*outputs))
results['mean_channel_difference']=sum(abs(a-b) for a,b in zip(*outputs))/len(outputs[0])
results['dimensions']=[w,h,dw,dh]
results['scope']='Synthetic offline image; native bilinear uses a different downsampling filter.'
print(json.dumps(results,indent=2))
