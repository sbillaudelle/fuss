import cairo
import pango
import pangocairo
import array


def get_text_preferred_size(text, font):

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1440, 460)
    
    ctx = cairo.Context(surface)
    ctx.set_source_rgb(.3, .3, .3)
    ctx.move_to(10, 10)
    pango_ctx = pangocairo.CairoContext(ctx)
    layout = pango_ctx.create_layout()
    layout.set_width(int(1024 * pango.SCALE))
    layout.set_font_description(font)
    layout.set_markup(text)

    return [i / pango.SCALE for i in layout.get_size()]


from PIL import Image
import ImageFilter
import numpy

def gaussian_grid(size = 5):
    """
    Create a square grid of integers of gaussian shape
    e.g. gaussian_grid() returns
    array([[ 1,  4,  7,  4,  1],
           [ 4, 20, 33, 20,  4],
           [ 7, 33, 55, 33,  7],
           [ 4, 20, 33, 20,  4],
           [ 1,  4,  7,  4,  1]])
    """
    m = size/2
    n = m+1  # remember python is 'upto' n in the range below
    x, y = numpy.mgrid[-m:n,-m:n]
    # multiply by a factor to get 1 in the corner of the grid
    # ie for a 5x5 grid   fac*exp(-0.5*(2**2 + 2**2)) = 1
    fac = numpy.exp(m**2)
    g = fac*numpy.exp(-0.5*(x**2 + y**2))
    return g.round().astype(int)


class GAUSSIAN(ImageFilter.BuiltinFilter):
    name = "Gaussian"
    gg = gaussian_grid().flatten().tolist()
    filterargs = (5, 5), sum(gg), 0, tuple(gg)


def blur(surface, iterations=3):

    width = surface.get_width()
    height = surface.get_height()

    img = Image.frombuffer("RGBA", (surface.get_width(), surface.get_height() ), surface.get_data(), "raw", "RGBA", 0, 1)

    for i in xrange(0, iterations):
        img = img.filter(GAUSSIAN)

    data = img.tostring()
    a = array.array('B', data)

    stride = width * 4
    surface = cairo.ImageSurface.create_for_data(a, cairo.FORMAT_ARGB32, width, height, stride)

    return surface
