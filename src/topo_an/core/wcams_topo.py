import rasterio
import numpy as np
from bokeh.models import LinearColorMapper, Slider, CustomJS
from bokeh.plotting import figure, save, output_file
from bokeh.layouts import column
from matplotlib.colors import LinearSegmentedColormap
from topo_an.core.geo_utils import XY_1_to_XY_2, osm_tile
from matplotlib.colors import to_hex


def read_wcams_topo(dir_wcams_topo):

    # list of wavecams ascii topo files
    ls = sorted(dir_wcams_topo.glob('*.asc'))

    # output list of topographies
    topos = []
    dates = []

    for i, f in enumerate(ls):
        with rasterio.open(f) as src:
            data = src.read(1)
            topo = np.ma.array(data, mask=data==-9999.)# Read first band
            # meta = src.meta
            topos.append(topo)
            if i == 0:
                bounds = src.bounds
            dates.append(f.stem.split('_')[-1])

    return topos, dates, bounds

def convert_mpl_colormap_to_hex(cmap, n_colors):

    # Generate colors from the colormap (e.g., 256 colors)
    colors_rgb = cmap(np.linspace(0, 1, n_colors))

    # Convert RGB values (0-1 range) to hex strings
    palette = [to_hex(rgb) for rgb in colors_rgb]

    return palette


def plot_wcams_topos(topos, dates, bounds, epsg, output_dir, tile_choice = 'Esri'):

    x, y = XY_1_to_XY_2(np.array([bounds.left, bounds.right]),
                              np.array([bounds.bottom, bounds.top]),
                              epsg,
                              '3857')
    x_min = np.min(x)
    x_max = np.max(x)
    y_min = np.min(y)
    y_max = np.max(y)

    # Convert all topo masked arrays to NaN arrays for Bokeh
    z = [np.flipud(np.where(topo.mask, np.nan, topo.data)) for topo in topos]

    # customized colormap. Edit this gradient at https://eltos.github.io/gradient/#0C0A69-2B4CD9-00E55A-FBFF03-9E6800-371B00
    cmap = LinearSegmentedColormap.from_list('my gradient', (
        # Edit this gradient at https://eltos.github.io/gradient/#0C0A69-2B4CD9-00E55A-FBFF03-F2B513-9E6800-371B00
        (0.000, (0.047, 0.039, 0.412)),
        (0.167, (0.169, 0.298, 0.851)),
        (0.333, (0.000, 0.898, 0.353)),
        (0.500, (0.984, 1.000, 0.012)),
        (0.667, (0.949, 0.710, 0.075)),
        (0.833, (0.620, 0.408, 0.000)),
        (1.000, (0.216, 0.106, 0.000))))
    palette = convert_mpl_colormap_to_hex(cmap, 256)

    # Setup color mapper
    color_mapper = LinearColorMapper(palette=palette, low=-3, high=4)
    color_mapper.nan_color = (0, 0, 0, 0)

    # Create figure
    p = figure(title="Intertidal topography", width=1536, height=864, x_axis_type="mercator", y_axis_type="mercator",
               match_aspect=True)

    # Add OSM tiles
    p.add_tile(osm_tile(tile_choice))

    # Hide grid lines
    p.grid.visible = False

    # plot topo
    img = p.image(image=[z[0]], x=x_min, y=y_min, dw=(x_max - x_min), dh=(y_max - y_min), color_mapper=color_mapper)

    # Create slider with CustomJS callback
    slider = Slider(start=0, end=len(z) - 1, step=1, value=0, title="INTERTIDAL TOPOGRAPHY", format=" ", width=1200)

    callback = CustomJS(args=dict(img=img,
                                  arrays=z,
                                  slider=slider,
                                  p=p,
                                  dates=dates), code="""
        const idx = slider.value;
        img.data_source.data['image'][0] = arrays[idx];
        img.data_source.change.emit();
        p.title.text = `${dates[idx]}`;
    """)

    slider.js_on_change('value', callback)

    output_file(output_dir.joinpath('wcams_topos.html'))
    layout = column(slider, p)
    save(layout)

    return