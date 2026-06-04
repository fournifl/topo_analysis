import numpy as np
from bokeh.models import WMTSTileSource
from bokeh.plotting import figure, save, output_file
from rasterio.crs import CRS
from rasterio.transform import array_bounds
from rasterio.warp import calculate_default_transform, reproject, Resampling

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

def calculate_tform_to_webmctor_and_reproj_extent(src):
    # calculate transform to web mercator (EPSG:3857) and reprojected extent
    dst_crs = CRS.from_epsg(3857)
    transform, width, height = calculate_default_transform(
        src.crs, dst_crs,
        src.width, src.height,
        *src.bounds
    )
    # Compute the reprojected extent. array_bounds returns (bottom, left, top, right) in the dst CRS
    left, bottom, right, top = array_bounds(height, width, transform)

    return dst_crs, transform, width, height, left, bottom, right, top

def get_common_mask(rio_topos):
    """
    This method computes the area where topography is defined at any time.

    Returns
    -------
    mask: numpy.ndarray
    """
    for i, rio_topo in enumerate(rio_topos):
        mask_i = rio_topo.read(1) == rio_topo.nodata
        if i == 0:
            mask = mask_i
        else:
            mask += mask_i
    return mask

def plot_common_mask(mask, topo_ex, outdir, tile_choice = 'Esri'):

    # calculate transform to web mercator (EPSG:3857) and reprojected extent
    dst_crs, tform, width, height, left, bottom, right, top = calculate_tform_to_webmctor_and_reproj_extent(topo_ex)

    nodata = 1

    # Reproject mask to Web Mercator
    dst_data = np.empty((height, width), dtype=float)
    reproject(
        source=mask.astype(int),
        destination=dst_data,
        src_transform=topo_ex.transform,
        src_crs=topo_ex.crs,
        dst_transform=tform,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
        src_nodata=nodata,
        dst_nodata=np.nan,
    )

    mask = np.zeros((height, width), dtype=float)
    mask[dst_data == 0] = 255

    # Flip: rasterio stores top→bottom, Bokeh needs bottom→top
    img = np.flipud(mask)

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
        image=[img],
        x=left,
        y=bottom,
        dw=(right - left),
        dh=(top - bottom),
        palette=["rgba(0,0,0,0)", "rgba(255,0,0,0.4)"]
    )
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    html = outdir.joinpath("common_mask.html")
    output_file(html)
    save(p)

    return


