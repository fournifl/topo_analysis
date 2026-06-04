from topo_an.core.topo import read_wcams_topo, read_sporadic_topos, apply_roi_mask_to_sporadic_topos
from topo_an.core.plot import plot_topos
from topo_an.core import stats

def run(wavecams_topos,
        sporadic_topos,
        output_dir
):

    # read wavecams topographies
    wc_rio_topos, wc_dates = read_wcams_topo(wavecams_topos.dir, wavecams_topos.epsg)

    # plot wavecams topographies
    plot_topos(wc_rio_topos, wc_dates, output_dir, name_out='wcams_topos', low=-3, high=4, type='WAVECAMS')

    # compute stats on wavecams topographies
    stats.d_volume(
        wc_rio_topos,
        wc_dates,
        wc_rio_topos[0],
        output_dir)

    # close wavecams topographies
    for ds in wc_rio_topos:
        ds.close()

    # read sporadic topographies
    sp_rio_topos = read_sporadic_topos(sporadic_topos.files)

    # apply roi mask to sporadic topographies
    sp_rio_topos = apply_roi_mask_to_sporadic_topos(sp_rio_topos, sporadic_topos.roi, output_dir)

    # plot sporadic topographies
    plot_topos(sp_rio_topos, sporadic_topos.date, output_dir, name_out='sporadic_topos', low=-4, high=12,
               type=', '.join(sporadic_topos.name))

    # compute stats on sporadic topographies

    # compute stats on sporadic topographies, on the same area than wcams' ones
    return