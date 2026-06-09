import matplotlib.pyplot as plt
import numpy as np

from topo_an.core.geo_utils import (get_common_mask, plot_common_mask, same_grid, align_rasters,
                                    reproject_rasters_to_web_mercator)
from topo_an.core.topo import get_bounds, get_pixel_surface
from topo_an.core.plot import plot_topos, plot_d_volume


def d_volume(rio_topos, dates, names, rio_topo_ref, output_dir, subdir):

    # output directory
    outdir = output_dir.joinpath('d_volume') / subdir
    outdir.mkdir(parents=True, exist_ok=True)

    # initialize variables
    mean_h = []
    t = []
    dh_with_ref = []
    dv_with_ref = []

    # reinterpolate on the same grid if necessary
    if not same_grid(rio_topos):
        print('align rasters')
        rio_topos, rio_topo_ref = align_rasters(rio_topos, rio_topo_ref)

    # compute common mask
    mask = get_common_mask(rio_topos)

    # plot common mask
    plot_common_mask(mask, rio_topos[0], outdir)

    # get the surface of a pixel
    ps = get_pixel_surface(rio_topos[0])

    # compute surface of common mask, in m2
    s = (~mask).sum() * ps

    # read and compress topo_ref
    topo_ref = rio_topo_ref.read(1).astype(float)
    topo_ref = np.ma.array(topo_ref, mask=topo_ref==rio_topo_ref.nodata)
    topo_ref.mask = mask
    topo_ref = topo_ref.compressed()

    # mean height follow up
    for i, rio_topo in enumerate(rio_topos):
        topo = rio_topo.read(1).astype(float)
        topo = np.ma.array(topo, mask=topo == rio_topo.nodata)
        topo.mask = mask
        topo = topo.compressed()
        mean_h.append(round(np.mean(topo), 2))
        t.append(dates[i])
        if rio_topo == rio_topo_ref:
            t_ref = dates[i]

        # mean volume follow up
        mean_d = round(np.mean(topo - topo_ref), 2)
        dh_with_ref.append(mean_d)
        dv_with_ref.append(mean_d * s)

    # plot volume differences of topographies
    plot_d_volume(names, mean_h, t, t_ref, dh_with_ref, dv_with_ref, outdir)

    # bokeh plot of topography differences with ref

    # reproject topos to web mercator (before bokeh plot)
    z, left, bottom, right, top = reproject_rasters_to_web_mercator(rio_topos)
    z_ref, _, _, _, _ = reproject_rasters_to_web_mercator([rio_topo_ref])
    rio_topo_ref.close()
    for rio_topo in rio_topos:
        rio_topo.close()
    dz = [z[i] - z_ref[0] for i in range(len(z))]

    plot_topos(dz, left, bottom, right, top, dates, outdir, name_out='dtopos', low=-1.5, high=1.5, name='', type='dtopo')

