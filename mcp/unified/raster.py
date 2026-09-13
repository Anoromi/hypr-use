"""Native screenshot downsampling, retaining the portal's geometry and PNG output."""
def install(cli):
    try:
        import gi
        gi.require_version('GdkPixbuf', '2.0')
        from gi.repository import GdkPixbuf, GLib
    except (ImportError, ValueError):
        return False  # Standalone runtimes retain the existing Python resizer.

    def resize(src, width, height, output_width, output_height):
        if min(width, height, output_width, output_height) <= 0:
            raise ValueError('invalid image dimensions')
        if len(src) != width * height * 4:
            raise ValueError('RGBA byte count mismatch')
        if (width, height) == (output_width, output_height):
            return src
        source = GdkPixbuf.Pixbuf.new_from_bytes(
            GLib.Bytes.new(src), GdkPixbuf.Colorspace.RGB, True, 8,
            width, height, width * 4)
        result = source.scale_simple(output_width, output_height, GdkPixbuf.InterpType.BILINEAR)
        if result is None:
            raise RuntimeError('Native screenshot resize failed')
        pixels, stride = result.get_pixels(), result.get_rowstride()
        return b''.join(pixels[y * stride:y * stride + output_width * 4]
                        for y in range(output_height))

    cli.resize_rgba_bilinear = resize
    return True
