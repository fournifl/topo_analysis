from topo_an.core import topo_validation

def main(conf):
    topo_validation.run(conf.validation.pairs,
                        conf.validation.outdir,
                        conf.wavecams_topos.epsg,
                        conf.sporadic_topos.epsg,
                        conf.sporadic_topos.roi)