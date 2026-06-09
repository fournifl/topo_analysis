import numpy as np
from dateutil import parser
import matplotlib.pyplot as plt
from bokeh.models import LinearColorMapper, Slider, CustomJS, ColorBar
from bokeh.plotting import figure, save, output_file
from bokeh.layouts import column
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import to_hex

from topo_an.core.geo_utils import osm_tile, reproject_rasters_to_web_mercator


def convert_mpl_colormap_to_hex(cmap, n_colors):

    # Generate colors from the colormap (e.g., 256 colors)
    colors_rgb = cmap(np.linspace(0, 1, n_colors))

    # Convert RGB values (0-1 range) to hex strings
    palette = [to_hex(rgb) for rgb in colors_rgb]

    return palette

def get_color_mapper(low=-5, high=5, type='topo'):

    if type == 'topo':
        # https://eltos.github.io/gradient/#0C0A69-2A5FD9-00E55A-FBFF03-F2B513-8B6316-371B00
        cmap = LinearSegmentedColormap.from_list('my gradient', (
            (0.000, (0.047, 0.039, 0.412)),
            (0.167, (0.165, 0.373, 0.851)),
            (0.333, (0.000, 0.898, 0.353)),
            (0.500, (0.984, 1.000, 0.012)),
            (0.667, (0.949, 0.710, 0.075)),
            (0.833, (0.545, 0.388, 0.086)),
            (1.000, (0.216, 0.106, 0.000))))
    elif type == 'dtopo':
        # https://eltos.github.io/gradient/#0C0A69-EAEAEA-FF000C
        cmap = LinearSegmentedColormap.from_list('my gradient', (
            (0.000, (0.047, 0.039, 0.412)),
            (0.500, (0.918, 0.918, 0.918)),
            (1.000, (1.000, 0.000, 0.047))))
    palette = convert_mpl_colormap_to_hex(cmap, 256)

    # Setup color mapper
    color_mapper = LinearColorMapper(palette=palette, low=low, high=high)
    color_mapper.nan_color = (0, 0, 0, 0)

    return color_mapper

def plot_topos(z, left, bottom, right, top, dates, output_dir, name_out, low=-5, high=5, name=None, type='topo'):

    # output directory
    outdir = output_dir.joinpath('plots')
    outdir.mkdir(parents=True, exist_ok=True)

    # set title
    if type =='topo':
        title = 'INTERTIDAL TOPOGRAPHY'
    elif type =='dtopo':
        title = 'TOPOGRAPHY DIFFERENCE'

    # set subtitle for each topo
    if isinstance(name, str):
        names = [name for i in range(len(z))]
    else:
        names = name
    subtitles = [dates[i] + ' ' + names[i] for i in range(len(dates))]

    # Create figure
    p = figure(title=subtitles[0], width=1536, height=864, x_axis_type="mercator",
               y_axis_type="mercator",
               match_aspect=True)

    # Add OSM tiles
    tile_choice = 'Esri'
    p.add_tile(osm_tile(tile_choice))

    # Hide grid lines
    p.grid.visible = False

    # color mapper
    color_mapper = get_color_mapper(low=low, high=high, type=type)

    # plot topo
    img = p.image(image=[z[0]], x=left, y=bottom, dw=(right - left), dh=(top - bottom), color_mapper=color_mapper)

    # Create slider with CustomJS callback
    slider = Slider(start=0, end=len(z) - 1, step=1, value=0, title=title, format=" ", width=1200, show_value=False)

    callback = CustomJS(args=dict(img=img,
                                  arrays=z,
                                  slider=slider,
                                  p=p,
                                  titles=subtitles), code="""
            const idx = slider.value;
            img.data_source.data['image'][0] = arrays[idx];
            img.data_source.change.emit();
            p.title.text = `${titles[idx]}`;
        """)

    slider.js_on_change('value', callback)

    # Colour bar
    color_bar = ColorBar(color_mapper=color_mapper, width=16, location=(0, 0), title="Elevation (mIGN69)",
    title_text_font_size="12pt", title_text_font_style="bold")
    p.add_layout(color_bar, "right")

    # Save plot
    output_file(outdir.joinpath(f'{name_out}.html'))
    print('\n --> ', outdir.joinpath(f'{name_out}.html'))
    layout = column(slider, p)
    save(layout)

    return

def plot_d_volume(names, mean_h, t, t_ref, dh_with_ref, dv_with_ref, outdir):

    # convert date arrays from string to datetime with dateuitl parser
    t = [parse_date(t) for t in t]
    t_ref = parse_date(t_ref)

    # convert variables to np arrays
    names = np.array(names)
    mean_h = np.array(mean_h)
    t = np.array(t)
    dh_with_ref = np.array(dh_with_ref)
    dv_with_ref = np.array(dv_with_ref)

    # create figure
    fig, ax = plt.subplots(3, 1, figsize=(16, 10), sharex=True)

    # find indices corresponding to wavecams or sporadic data
    inds_wcams = np.where(names == 'WAVECAMS')[0]
    inds_spor = np.where(names !='WAVECAMS')[0]

    # plot mean beach height
    # wavecams
    ax[0].axvline(x=t_ref, color='aqua', label='ref', linewidth=3.5)
    if len(inds_wcams) > 0:
        ax[0].plot(t[inds_wcams], mean_h[inds_wcams], color='darkblue', linewidth=2, marker='d', markersize=4,
                   label='wavecams')
    # sporadic
    if len(inds_spor) > 0:
        ax[0].plot(t[inds_spor], mean_h[inds_spor], color='limegreen', linewidth=0, marker='s', markersize=5,
                   label='sporadic')
    ax[0].set_title('MEAN BEACH HEIGHT')
    ax[0].grid(True)
    ax[0].set_ylabel('mean_h (m)', color='darkblue')
    ax[0].legend(loc='upper right', fontsize=12)

    # plot mean beach height difference with ref
    ax[1].axvline(x=t_ref, color='aqua', label='ref', linewidth=3.5)
    # wavecams
    if len(inds_wcams) > 0:
        ax[1].plot(t[inds_wcams], dh_with_ref[inds_wcams], color='darkblue', linewidth=2, marker='d', markersize=4,
                   label='wavecams')
    # sporadic
    if len(inds_spor) > 0:
        ax[1].plot(t[inds_spor], dh_with_ref[inds_spor], color='limegreen', linewidth=0, marker='s', markersize=5,
                   label='sporadic')

    ax[1].legend(loc='upper right', fontsize=12)
    ax[1].set_title('MEAN HEIGHT DIFFERENCE WITH REF TOPO')
    ax[1].set_ylabel('H difference (m)', color='darkblue')
    ax[1].axhline(y=0, linewidth=2, color='gray', dashes=(4, 4))
    ax[1].set_xlim([min(t), max(t)])
    ax[1].tick_params(axis='y', labelcolor='darkblue')
    ax[1].grid(True)

    # plot volume difference with ref
    ax[2].axvline(x=t_ref, color='aqua', label='ref', linewidth=3.5)
    # wavecams
    if len(inds_wcams) > 0:
        ax[2].plot(t[inds_wcams], dv_with_ref[inds_wcams], color='red', linewidth=2, marker='d', markersize=4,
                   label='wavecams')
    # sporadic
    if len(inds_spor) > 0:
        ax[2].plot(t[inds_spor], dv_with_ref[inds_spor], color='limegreen', linewidth=0, marker='s', markersize=5,
                   label='sporadic')
    ax[2].set_title('VOLUME DIFFERENCE WITH REF TOPO')
    ax[2].set_ylabel('V difference (m3)', color='red')
    ax[2].axhline(y=0, linewidth=2, color='gray', dashes=(4, 4))
    ax[2].tick_params(axis='y', labelcolor='red')
    ax[2].grid(True)
    ax[2].legend(loc='upper right', fontsize=12)
    fig.autofmt_xdate()
    jpg = outdir.joinpath("d_volume.jpg")
    fig.savefig(jpg, bbox_inches='tight')
    print("\n --> %s \n" % jpg)
    return

def parse_date(date_string):
    date = parser.parse(date_string)

    return date

