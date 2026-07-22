import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import array_bounds
from rasterio.warp import calculate_default_transform, reproject, Resampling

def calculate_tform_and_reproj_extent(src, crs=3857):
    # calculate transform to web mercator by default (EPSG:3857) and reprojected extent
    dst_crs = CRS.from_epsg(crs)
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

def reproject_rasters(src_topos):

    # initialize reprojected variables
    z = []

    # calculate transform to web mercator (EPSG:3857) and reprojected extent
    dst_crs, tform, width, height, left, bottom, right, top = calculate_tform_and_reproj_extent(
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
    Reproject all rasters onto the grid of reference one.
    Returns a list of objects rasterio.io.DatasetWriter.
    """

    rio_aligned = []

    profile = rio_ref.profile.copy()

    for src in raster_list:
        if src == rio_ref:
            rio_aligned.append(src)  # already on the right grid
        else:
            aligned = reproject_to_grid(src, rio_ref)
            profile.update(count=aligned.shape[0], dtype=aligned.dtype)
            out_path = src.name.replace(".tif", "_aligned.tif")
            with rasterio.open(out_path, "w", **profile) as dst:
                dst.write(aligned)
            src_aligned = rasterio.open(out_path, 'r+')
            rio_aligned.append(src_aligned)

    return rio_aligned


