import numpy as np
import shutil
from topo_an.core.topo import open_wcams_topo, open_sporadic_topos, apply_roi_mask_to_sporadic_topos
from topo_an.core.geo_utils import same_grid, align_rasters, reproject_rasters
from topo_an.core.stats import validation_metrics
from topo_an.core.plot import plot_validation, gather_validation_layouts


def run(pairs, outdir, epsg_wcams, epsg_spor, roi_spor):
    layouts_val = []

    # loop through each validation pair
    for i in range(len(pairs)):

        # open wavecams topography
        wc_rio_topo, wc_date = open_wcams_topo(pairs[i].wavecams, epsg_wcams)

        # open sporadic topography
        sp_rio_topo = open_sporadic_topos([pairs[i].sporadic], epsg_spor)

        # apply roi mask to sporadic topography
        outdir_masked = outdir / 'sporadic_topos_masked'
        sp_rio_topo = apply_roi_mask_to_sporadic_topos(sp_rio_topo, roi_spor, outdir_masked)[0]

        # reinterpolate on the same grid if necessary
        if not same_grid([wc_rio_topo, sp_rio_topo]):
            print('align rasters before validation')
            sp_rio_topo = align_rasters([sp_rio_topo], wc_rio_topo)[0]

        # read wavecams topography
        wc_topo = wc_rio_topo.read(1).astype(float)
        wc_topo = np.ma.array(wc_topo, mask=wc_topo == wc_rio_topo.nodata)

        # read independent sporadic topography
        sp_topo = sp_rio_topo.read(1).astype(float)
        sp_topo = np.ma.array(sp_topo, mask=sp_topo == sp_rio_topo.nodata)

        rmse, mae, corr = validation_metrics(wc_topo, sp_topo)

        # reproject topos to web mercator (before bokeh plot)
        [wc_topo, sp_topo], left, bottom, right, top = reproject_rasters([wc_rio_topo, sp_rio_topo])

        layout_val = plot_validation(wc_topo, sp_topo, rmse, mae, corr, left, bottom, right, top, i)
        layouts_val.append(layout_val)

        wc_rio_topo.close()
        sp_rio_topo.close()

    # rm temporary directory of masked data
    shutil.rmtree(outdir_masked)

    # gather all layouts
    gather_validation_layouts(layouts_val, outdir)

    return