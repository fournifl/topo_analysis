from topo_an.core.wcams_topo import read_wcams_topo, plot_wcams_topos
from topo_an.core import stats

def run(wavecams_topos,
        ponctual_topos,
        output_dir
):

    # read wavecams topographies
    wc_topos, wc_dates, bounds = read_wcams_topo(wavecams_topos.dir)

    # plot wavecams topographies
    plot_wcams_topos(wc_topos, wc_dates, bounds, wavecams_topos.epsg, output_dir)

    # compute stats on topographies
    stats.d_volume(wc_topos, wc_dates, bounds, wc_topos[0], wavecams_topos.epsg, output_dir)

    return