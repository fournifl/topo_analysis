import matplotlib.pyplot as plt
import numpy as np

from topo_an.core.geo_utils import get_common_mask, plot_common_mask, same_grid, align_rasters
from topo_an.core.topo import get_bounds, get_pixel_surface


def d_volume(rio_topos, dates, rio_topo_ref, output_dir, subdir):

    # output directory
    outdir = output_dir.joinpath('d_volume') / subdir
    outdir.mkdir(parents=True, exist_ok=True)

    # initialize variables
    mean_h = []
    time_h = []
    time_d = []
    dh_with_ref_topo = []
    dv_with_ref_topo = []

    # reinterpolate on the same grid if necessary (
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
        time_h.append(dates[i])

        # mean volume follow up
        mean_d = round(np.mean(topo - topo_ref), 2)
        # compute volume difference only if topo is not the reference topo
        if abs(mean_d) > 0:
            dh_with_ref_topo.append(mean_d)
            dv_with_ref_topo.append(mean_d * s)
            time_d.append(dates[i])

    # plot stats of topographies
    plot_d_volume(mean_h,
                  time_h,
                  dh_with_ref_topo,
                  dv_with_ref_topo,
                  time_d,
                  outdir)

    return

def plot_d_volume(mean_h, time_h, dh_with_ref_topo, dv_with_ref_topo, time_d, outdir):
    f, ax = plt.subplots(3, 1, figsize=(16, 10), sharex=True)

    ax[0].plot(time_h, mean_h, color='darkblue', linewidth=2, marker='d', markersize=4,
               label='mean beach height (m)')
    ax[0].set_title('MEAN BEACH HEIGHT')
    ax[0].grid(True)
    ax[0].set_ylabel('mean_h (m)', color='darkblue')
    ax[0].legend(loc='lower right', fontsize=14)

    ax[1].plot(time_d, dh_with_ref_topo, color='darkblue', linewidth=2, marker='d', markersize=4,
               label='mean beach height difference (m)')
    ax[1].legend(loc='lower right', fontsize=14)
    ax[1].set_title('MEAN HEIGHT DIFFERENCE WITH FIRST TOPO')
    ax[1].set_ylabel('H difference (m)', color='darkblue')
    ax[1].axhline(y=0, linewidth=2, color='gray', dashes=(4, 4))
    ax[1].set_xlim([min(time_h), max(time_h)])
    ax[1].tick_params(axis='y', labelcolor='darkblue')
    ax[1].grid(True)
    ax[2].plot(time_d, dv_with_ref_topo, color='red', linewidth=2, marker='d', markersize=4,
               label='mean beach volume difference (m3)')
    ax[2].set_title('VOLUME DIFFERENCE WITH FIRST TOPO')
    ax[2].set_ylabel('V difference (m3)', color='red')
    ax[2].axhline(y=0, linewidth=2, color='gray', dashes=(4, 4))
    ax[2].tick_params(axis='y', labelcolor='red')
    ax[2].grid(True)
    ax[2].legend(loc='lower right', fontsize=14)
    f.autofmt_xdate()
    jpg = outdir.joinpath("d_volume.jpg")
    f.savefig(jpg, bbox_inches='tight')
    print("\n --> %s \n" % jpg)
