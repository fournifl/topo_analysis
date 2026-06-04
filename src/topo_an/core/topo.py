import rasterio
from rasterio.crs import CRS

def read_wcams_topo(dir_wcams_topo, epsg):

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
        dates.append(f.stem.split('_')[-1])

    return rio_topos, dates
