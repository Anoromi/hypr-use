"""Reduce screenshot wire bytes without changing coordinate geometry."""
import base64
import os
import time


def optimize_images(result):
    mode = os.environ.get('HYPR_USE_IMAGE_FORMAT', 'auto')
    if mode not in ('auto', 'png'):
        raise ValueError('HYPR_USE_IMAGE_FORMAT must be auto or png')
    if mode == 'png' or not isinstance(result, dict):
        return
    blocks = result.get('content', [])
    candidates = [b for b in blocks if b.get('type') == 'image' and b.get('mimeType') == 'image/png']
    if not candidates:
        return
    import gi
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf
    stats = []
    for block in candidates:
        original = base64.b64decode(block['data'], validate=True)
        if len(original) < 128 * 1024:
            continue
        start = time.monotonic()
        loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        loader.write(original)
        loader.close()
        pix = loader.get_pixbuf()
        # Keep real transparency lossless. Opaque RGBA screenshots are safe to encode.
        if pix.get_has_alpha():
            pixels, stride = pix.get_pixels(), pix.get_rowstride()
            if any(pixels[y * stride + 3:y * stride + pix.get_width() * 4:4].count(255) != pix.get_width()
                   for y in range(pix.get_height())):
                continue
        ok, encoded = pix.save_to_bufferv('jpeg', ['quality'], ['85'])
        if not ok:
            raise RuntimeError('Screenshot JPEG encoding failed')
        if len(encoded) < len(original):
            block['data'] = base64.b64encode(encoded).decode('ascii')
            block['mimeType'] = 'image/jpeg'
        stats.append({'original_bytes': len(original),
                      'output_bytes': len(encoded) if len(encoded) < len(original) else len(original),
                      'mime_type': block['mimeType'], 'width': pix.get_width(),
                      'height': pix.get_height(), 'encoding_ms': (time.monotonic()-start)*1000})
    if stats:
        result.setdefault('_meta', {})['hypr-use/images'] = stats
