"""Candidate only: conservatively detect a full-viewport document in another scale."""
import math

def document_scale(bounds,root):
 if not bounds or not root:return None
 # Restrict inference to local Wayland roots. Global/mixed origins need explicit
 # metadata; do not guess from an arbitrary oversized descendant or web page.
 if abs(root['x'])>.01 or abs(root['y'])>.01 or abs(bounds['x'])>2:return None
 if root['width']<=0 or root['height']<=0:return None
 sx=bounds['width']/root['width'];sy=(bounds['y']+bounds['height'])/root['height']
 if not all(math.isfinite(x) for x in [sx,sy]) or not 1.1<=sx<=4:return None
 if abs(sx-sy)>0.01*max(sx,sy):return None
 return (sx+sy)/2

def normalize(bounds,scale):return {k:v/scale for k,v in bounds.items()} if bounds and scale else bounds
