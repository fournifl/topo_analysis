from pyproj import Transformer
import numpy as np
from bokeh.models import WMTSTileSource
from bokeh.plotting import figure, save, output_file

def XY_1_to_XY_2(X, Y, epsg_in, epsg_out):
    """
    Convert coordinates defined in inProj projection, to outProj Projection
    """
    shape = X.shape
    X = X.flatten()
    Y = Y.flatten()
    transformer = Transformer.from_crs(int(epsg_in), int(epsg_out), always_xy=True)
    X2, Y2 = transformer.transform(X, Y)
    X2 = np.reshape(X2, shape)
    Y2 = np.reshape(Y2, shape)
    return X2, Y2

def osm_tile(tile_choice):

    # OSM tiles
    if tile_choice == 'carto_light':
        tile = WMTSTileSource(
            url='https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{Z}/{X}/{Y}.png',
            attribution='&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attributions">CARTO</a>'
        )

    elif tile_choice == "Esri":
        tile = "Esri World Imagery"

    return tile

def get_grid(bounds, topos):

    # get topo grid
    grid_x, grid_y = np.meshgrid(np.linspace(bounds.left, bounds.right, topos[0].shape[0]),
                                 np.linspace(bounds.bottom, bounds.top, topos[0].shape[1]))

    return grid_x, grid_y

def get_common_mask(topos):
    """
    This method computes the area where topography is defined at any time.

    Returns
    -------
    mask: numpy.ndarray
    """
    for i, topo in enumerate(topos):
        if i == 0:
            mask = topo.mask
        else:
            mask += topo.mask
    return mask

def plot_common_mask(mask, bounds, epsg, outdir, tile_choice = 'Esri'):

    x, y = XY_1_to_XY_2(np.array([bounds.left, bounds.right]),
                        np.array([bounds.bottom, bounds.top]),
                        epsg,
                        '3857')
    x_min = np.min(x)
    x_max = np.max(x)
    y_min = np.min(y)
    y_max = np.max(y)

    # Create figure in Web Mercator
    p = figure(
        x_axis_type="mercator",
        y_axis_type="mercator",
        width=800,
        height=600
    )

    # Add OSM tile
    p.add_tile(osm_tile(tile_choice))

    # plot mask
    p.image(
        image=[np.flipud(mask)],
        x=x_min,
        y=y_min,
        dw=(x_max - x_min),
        dh=(y_max - y_min),
        palette=["rgba(255,0,0,0.4)", "rgba(0,0,0,0)"]
    )
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    html = outdir.joinpath("common_mask.html")
    output_file(html)
    save(p)

    return


