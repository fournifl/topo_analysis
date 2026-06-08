import numpy as np
from bokeh.models import WMTSTileSource
from bokeh.plotting import figure, save, output_file
import rasterio
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

def same_grid(ls):
    check_crs = all(ls[i].crs == ls[0].crs for i in range(len(ls)))
    check_transform = all(ls[i].transform == ls[0].transform for i in range(len(ls)))
    check_shape = all(ls[i].shape == ls[0].shape for i in range(len(ls)))
    same_grid = all([check_crs, check_transform, check_shape])
    return same_grid

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

def reproject_rasters_to_web_mercator(src_topos):

    # initialize reprojected variables
    z = []

    # calculate transform to web mercator (EPSG:3857) and reprojected extent
    dst_crs, tform, width, height, left, bottom, right, top = calculate_tform_to_webmctor_and_reproj_extent(
        src_topos[0])

    for i, src in enumerate(src_topos):

        # read topo data
        src_data = src.read(1).astype(float)  # band 1
        nodata = src.nodata

        # Reproject topo to Web Mercator
        dst_data = np.empty((height, width), dtype=np.float32)
        reproject(
            source=src_data,
            destination=dst_data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=tform,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear,
            src_nodata=nodata,
            dst_nodata=np.nan,
        )

        # Mask nodata
        if nodata is not None:
            dst_data[dst_data == nodata] = np.nan

        # Flip: rasterio stores top→bottom, Bokeh needs bottom→top
        img = np.flipud(dst_data)
        z.append(img)

    return z, left, bottom, right, top


# align rasters functions:
def get_area(src):
    """Return the geographic area covered by a raster."""
    bounds = src.bounds
    return (bounds.right - bounds.left) * (bounds.top - bounds.bottom)

def get_least_extended(raster_list):
    """Return the raster with the smallest geographic extent."""
    return min(raster_list, key=get_area)

def reproject_to_grid(src, ref):
    """
    Reproject `src` onto the grid defined by `ref`.
    Returns a numpy array with shape (bands, height, width).
    """
    out = np.empty(
        (src.count, ref.height, ref.width),
        dtype=src.dtypes[0]
    )

    reproject(
        source=rasterio.band(src, list(range(1, src.count + 1))),
        destination=out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=ref.transform,
        dst_crs=ref.crs,
        resampling=Resampling.bilinear,  # change as needed
    )
    return out

def align_rasters(raster_list, rio_ref):
    """
    Reproject all rasters onto the grid of the least extended one.
    Returns a list of numpy arrays, all on the same grid.
    """
    ref_alignment = get_least_extended(raster_list)
    print(f"Reference grid: shape={ref_alignment.shape}, crs={ref_alignment.crs}, transform={ref_alignment.transform}")

    rio_aligned = []

    profile = ref_alignment.profile.copy()
    for src in raster_list:
        if src == ref_alignment:
            rio_aligned.append(src)  # already on the right grid
            if src == rio_ref:
                rio_ref = src
        else:
            aligned = reproject_to_grid(src, ref_alignment)
            profile.update(count=aligned.shape[0], dtype=aligned.dtype)
            out_path = src.name.replace(".tif", "_aligned.tif")
            with rasterio.open(out_path, "w", **profile) as dst:
                dst.write(aligned)
                src_aligned = rasterio.open(out_path, 'r+')
            rio_aligned.append(src_aligned)
            if src == rio_ref:
                rio_ref = src_aligned
    # Close all sources
    # for src in raster_list:
    #     if src != ref:
    #         src.close()
    return rio_aligned, rio_ref


