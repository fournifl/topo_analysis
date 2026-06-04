from topo_an.core import topo_analysis

def main(conf):
    topo_analysis.run(
        conf.wavecams_topos,
        conf.sporadic_topos,
        conf.output_dir
    )