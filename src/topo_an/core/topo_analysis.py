import numpy as np
import shutil

from topo_an.core.topo import open_wcams_topo, open_sporadic_topos, apply_roi_mask_to_sporadic_topos
from topo_an.core.plot import plot_topos
from topo_an.core import stats
from topo_an.core.geo_utils import reproject_rasters_to_web_mercator

def run_wcams(wavecams_topos, outdir):

    # open wavecams topographies
    wc_rio_topos, wc_dates = open_wcams_topo(wavecams_topos.dir, wavecams_topos.epsg)

    # reproject topos to web mercator (before bokeh plot)
    z, left, bottom, right, top = reproject_rasters_to_web_mercator(wc_rio_topos)

    # plot wavecams topographies
    plot_topos(z, left, bottom, right, top, wc_dates, outdir, 'topos_plot',name_out='wcams_topos', low=-3,
               high=4, name='WAVECAMS')

    # wavecams' topography names
    wc_names = ['WAVECAMS' for i in range(len(wc_rio_topos))]

    # compute stats on wavecams topographies
    stats.d_volume(wc_rio_topos, wc_dates, wc_names, wc_rio_topos[0], outdir, 'wavecams')

    # close wavecams topographies
    for ds in wc_rio_topos:
        ds.close()

def run_spor(sporadic_topos, outdir):

    # open sporadic topographies
    sp_rio_topos = open_sporadic_topos(sporadic_topos.files, sporadic_topos.epsg)

    # apply roi mask to sporadic topographies
    outdir_masked = outdir / 'sporadic_topos_masked'
    sp_rio_topos = apply_roi_mask_to_sporadic_topos(sp_rio_topos, sporadic_topos.roi, outdir_masked)

    # reproject topos to web mercator (before bokeh plot)
    z, left, bottom, right, top = reproject_rasters_to_web_mercator(sp_rio_topos)

    # plot sporadic topographies
    plot_topos(z, left, bottom, right, top, sporadic_topos.date, outdir, 'topos_plot', name_out='sporadic_topos',
               low=-4, high=12, name=sporadic_topos.name)

    # compute stats on sporadic topographies
    stats.d_volume(sp_rio_topos, sporadic_topos.date, sporadic_topos.name, sp_rio_topos[0], outdir,'sporadic')

    # close sporadic topographies
    for ds in sp_rio_topos:
        ds.close()

    # rm temporary directory of masked data
    shutil.rmtree(outdir_masked)

def run_all(wavecams_topos, sporadic_topos, outdir):
    '''
    compute stats on both wavecams and sporadic topographies (on the same area than wcams' one)
    '''

    # open wavecams topographies
    wc_rio_topos, wc_dates = open_wcams_topo(wavecams_topos.dir, wavecams_topos.epsg)

    # open sporadic topographies
    sp_rio_topos = open_sporadic_topos(sporadic_topos.files, sporadic_topos.epsg)

    # apply roi mask to sporadic topographies
    outdir_masked = outdir / 'sporadic_topos_masked'
    sp_rio_topos = apply_roi_mask_to_sporadic_topos(sp_rio_topos, sporadic_topos.roi, outdir_masked)

    # gather opened topographies
    dates = wc_dates + sporadic_topos.date
    inds_t = np.argsort(dates)
    dates = [dates[i] for i in inds_t]
    rio_topos = np.array((wc_rio_topos + sp_rio_topos))
    rio_topos = [rio_topos[i] for i in inds_t]

    # gather topography names
    wc_names = ['WAVECAMS' for i in range(len(wc_rio_topos))]
    sp_names = sporadic_topos.name
    name_ = wc_names + sp_names
    name = [name_[i] for i in inds_t]

    # reproject topos to web mercator (before bokeh plot)
    z, left, bottom, right, top = reproject_rasters_to_web_mercator(rio_topos)

    # plot wavecams and sporadic topographies
    plot_topos(z, left, bottom, right, top, dates, outdir, 'topos_plot', name_out='wcams_sporadic_topos', low=-4,
               high=12, name=name)

    # compute stats
    stats.d_volume(rio_topos, dates, name, wc_rio_topos[0], outdir, 'wavecams_sporadic')

    # close wavecams, sporadic topographies
    for ds in rio_topos:
        ds.close()

    # rm temporary directory of masked data
    shutil.rmtree(outdir_masked)

    return
