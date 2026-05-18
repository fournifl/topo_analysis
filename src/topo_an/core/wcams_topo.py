import rasterio
import numpy as np
from bokeh.models import WMTSTileSource, LinearColorMapper, Slider, CustomJS
from bokeh.plotting import figure, show, save, output_file
from bokeh.layouts import column
import colorcet as cc
from topo_an.core.geo_utils import XY_1_to_XY_2

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
            if i ==0:
                bounds = src.bounds
            dates.append(f.stem.split('_')[-1])
    return topos, dates, bounds


def plot_wcams_topos(topos, dates, bounds, epsg, tile_choice = 'Esri'):

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

    # Setup color mapper
    color_mapper = LinearColorMapper(palette=cc.rainbow, low=-3, high=4)
    color_mapper.nan_color = (0, 0, 0, 0)

    # Create figure
    p = figure(title="Intertidal topography", width=1536, height=864, x_axis_type="mercator", y_axis_type="mercator",
               match_aspect=True)

    # ---- Add OSM tiles ----
    if tile_choice == 'carto_light':
        tile = WMTSTileSource(
            url='https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{Z}/{X}/{Y}.png',
            attribution='&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attributions">CARTO</a>'
        )
    elif tile_choice == "Esri":
        tile = "Esri World Imagery"
    p.add_tile(tile)

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

    output_file('test.html')
    layout = column(slider, p)
    save(layout)

    return