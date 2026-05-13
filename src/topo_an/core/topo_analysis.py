from topo_an.core.wcams_topo import read_wcams_topo, plot_wcams_topos

def run(wavecams_topos,
        ponctual_topos,
        output_dir
):

    # read wavecams topographies
    wc_topos, bounds = read_wcams_topo(wavecams_topos.dir)

    # plot wavecams topographies
    plot_wcams_topos(wc_topos, bounds, wavecams_topos.epsg)


    return