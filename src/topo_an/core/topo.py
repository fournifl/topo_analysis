import rasterio
from rasterio.crs import CRS
from rasterio.mask import mask
from rasterio.io import MemoryFile
import geopandas as gpd
from pathlib import Path

def open_wcams_topo(dir_wcams_topo, epsg):

    # list of wavecams ascii topo files
    ls = sorted(dir_wcams_topo.glob('*.asc'))

    # output list of rio topography objects
    rio_topos = []
    dates = []

    for i, f in enumerate(ls):

        # create rio object
        src = rasterio.open(f, 'r+')

        # set crs
        src.crs = CRS.from_epsg(epsg)

        # append rio object to list
        rio_topos.append(src)

        # append date to dates
        date = f.stem.split('_')[-1]
        dates.append(f'{date[0:4]}-{date[4:6]}-{date[6:8]}')

    return rio_topos, dates

def open_sporadic_topos(ls_spor_topos, epsg):

    # output list of rio topography objects
    rio_topos = []

    for i, f in enumerate(ls_spor_topos):
        # create rio object
        src = rasterio.open(f, 'r+')

        # set crs if necessary
        if src.crs is None:
            src.crs = CRS.from_epsg(epsg)

        # append rio object to list
        rio_topos.append(src)

    return rio_topos

def apply_roi_mask_to_sporadic_topos(sp_rio_topos, roi, output_dir):

    # output dir masked data
    output_dir_masked = Path(output_dir / 'sporadic_topos_masked')
    output_dir_masked.mkdir(exist_ok=True, parents=True)

    # read roi from the GeoPackage
    roi = gpd.read_file(roi)

    sp_rio_topos_masked = []

    # Reproject roi polygon to match raster CRS if necessary
    if roi.crs != sp_rio_topos[0].crs:
        roi = roi.to_crs(sp_rio_topos[0].crs)

    shapes = roi.geometry.values  # list of shapely geometries

    # Apply the mask
    for i, sp_rio_topo in enumerate(sp_rio_topos):
        masked_data, masked_transform = mask(sp_rio_topo, shapes,
            crop=True,  # crop the output extent to the polygon bounds
            nodata=-9999,  # value assigned to pixels outside the polygon
            filled=True  # fill masked pixels with nodata value
        )
        # Update metadata
        masked_meta = sp_rio_topo.meta.copy()
        masked_meta.update({
            "height": masked_data.shape[1],
            "width": masked_data.shape[2],
            "transform": masked_transform,
            "nodata": -9999
        })

        # write masked data
        fname = output_dir_masked / Path(sp_rio_topo.name).name
        with rasterio.open(fname, "w", **masked_meta) as dest:
            dest.write(masked_data)
        sp_rio_topo.close()

        sp_rio_topos_masked.append(rasterio.open(fname, 'r+'))

    return sp_rio_topos_masked

def get_bounds(src):
    bounds = src.bounds
    return bounds

def get_pixel_surface(src):
    # grid_resolution
    x_res = src.transform[0]
    y_res = - src.transform[4]

    # surface of a pixel
    ps = x_res * y_res

    return ps
