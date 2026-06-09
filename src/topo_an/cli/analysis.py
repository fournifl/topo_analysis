from topo_an.core import topo_analysis

def main(conf):

    topo_analysis.run_wcams(
        conf.wavecams_topos,
        conf.output_dir
    )

    topo_analysis.run_spor(
        conf.sporadic_topos,
        conf.output_dir
    )

    topo_analysis.run_all(
        conf.wavecams_topos,
        conf.sporadic_topos,
        conf.output_dir
    )