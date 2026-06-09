import numpy as np
from dateutil import parser
import matplotlib.pyplot as plt
from bokeh.models import LinearColorMapper, Slider, CustomJS, ColorBar, Span, WMTSTileSource
from bokeh.plotting import figure, save, output_file
from bokeh.layouts import column, row
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import to_hex
from rasterio.warp import reproject, Resampling
from topo_an.core.geo_utils import calculate_tform_to_webmctor_and_reproj_extent, get_common_mask


def osm_tile(tile_choice):

    # OSM tiles
    if tile_choice == 'carto_light':
        tile = WMTSTileSource(
            url='https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{Z}/{X}/{Y}.png',
            attribution='&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy; <a href="https://carto.com/attributions">CARTO</a>'
        )

    elif tile_choice == "Esri":
        tile = "Esri World Imagery"

    return tile

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
        # cmap = LinearSegmentedColormap.from_list('my gradient', (
        #     (0.000, (0.047, 0.039, 0.412)),
        #     (0.500, (0.918, 0.918, 0.918)),
        #     (1.000, (1.000, 0.000, 0.047))))
        cmap = LinearSegmentedColormap.from_list('my gradient', (
            # Edit this gradient at https://eltos.github.io/gradient/#0C0A69-0079FF-EAEAEA-ED8900-FF000C
            (0.000, (0.047, 0.039, 0.412)),
            (0.250, (0.000, 0.475, 1.000)),
            (0.500, (0.918, 0.918, 0.918)),
            (0.750, (0.929, 0.537, 0.000)),
            (1.000, (1.000, 0.000, 0.047))))
    palette = convert_mpl_colormap_to_hex(cmap, 256)

    # Setup color mapper
    color_mapper = LinearColorMapper(palette=palette, low=low, high=high)
    color_mapper.nan_color = (0, 0, 0, 0)

    return color_mapper

def plot_topos(z, left, bottom, right, top, dates, output_dir, subdir, name_out, low=-5, high=5, name=None, type='topo'):

    # output directory
    outdir = output_dir.joinpath(subdir)
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

def plot_d_volume_bokeh(names, mean_h, t, t_ref, dh_with_ref, dv_with_ref, outdir, rio_topos=None):

    # convert date arrays from string to datetime with dateutil parser
    t = [parse_date(t) for t in t]
    t_ref = parse_date(t_ref)

    # convert variables to np arrays
    names = np.array(names)
    mean_h = np.array(mean_h)
    t = np.array(t)
    dh_with_ref = np.array(dh_with_ref)
    dv_with_ref = np.array(dv_with_ref)

    # find indices corresponding to wavecams or sporadic data
    inds_wcams = np.where(names == 'WAVECAMS')[0]
    inds_spor = np.where(names != 'WAVECAMS')[0]

    # Create three figures stacked vertically
    p1 = figure(width=1200, height=250, x_axis_type='datetime', title='MEAN BEACH HEIGHT')
    p2 = figure(width=1200, height=250, x_axis_type='datetime', title='MEAN HEIGHT DIFFERENCE WITH REF TOPO')
    p3 = figure(width=1200, height=250, x_axis_type='datetime', title='VOLUME DIFFERENCE WITH REF TOPO')

    # Reference line (vertical) - same for all plots
    ref_line = Span(location=t_ref, dimension='height', line_color='aqua', line_width=3.5)
    p1.add_layout(ref_line)
    p2.add_layout(ref_line)
    p3.add_layout(ref_line)

    # Add ref_line to legend using dummy invisible lines
    p1.line([t_ref, t_ref], [mean_h.min(), mean_h.max()], color='aqua', line_width=3.5, legend_label='ref', alpha=1)

    # Wavecams data (darkblue diamond markers)
    if len(inds_wcams) > 0:
        p1.scatter(t[inds_wcams], mean_h[inds_wcams], size=6, color='darkblue', marker='diamond', legend_label='wavecams')
        p1.line(t[inds_wcams], mean_h[inds_wcams], color='darkblue', line_width=2)
        p2.scatter(t[inds_wcams], dh_with_ref[inds_wcams], size=6, color='darkblue', marker='diamond', legend_label='wavecams')
        p2.line(t[inds_wcams], dh_with_ref[inds_wcams], color='darkblue', line_width=2)
        p3.scatter(t[inds_wcams], dv_with_ref[inds_wcams], size=6, color='red', marker='diamond', legend_label='wavecams')
        p3.line(t[inds_wcams], dv_with_ref[inds_wcams], color='red', line_width=2)

    # Sporadic data (limegreen square markers)
    if len(inds_spor) > 0:
        p1.scatter(t[inds_spor], mean_h[inds_spor], size=6, color='limegreen', marker='square', legend_label='sporadic')
        p2.scatter(t[inds_spor], dh_with_ref[inds_spor], size=6, color='limegreen', marker='square', legend_label='sporadic')
        p3.scatter(t[inds_spor], dv_with_ref[inds_spor], size=6, color='limegreen', marker='square', legend_label='sporadic')

    # Horizontal line at y=0 for plots 2 and 3
    hline_p2 = Span(location=0, dimension='width', line_color='gray', line_width=2, line_dash='dashed')
    hline_p3 = Span(location=0, dimension='width', line_color='gray', line_width=2, line_dash='dashed')
    p2.add_layout(hline_p2)
    p3.add_layout(hline_p3)

    # Y-axis labels and colors
    p1.yaxis.axis_label = 'mean_h (m)'
    p1.yaxis.axis_label_text_color = 'black'
    p2.yaxis.axis_label = 'H difference (m)'
    p2.yaxis.axis_label_text_color = 'black'
    p3.yaxis.axis_label = 'V difference (m3)'
    p3.yaxis.axis_label_text_color = 'red'

    # Grid and legend settings
    p1.grid.visible = True
    p2.grid.visible = True
    p3.grid.visible = True
    p1.legend.location = 'top_right'
    p1.legend.label_text_font_size = '12pt'
    p2.legend.location = 'top_right'
    p2.legend.label_text_font_size = '12pt'
    p3.legend.location = 'top_right'
    p3.legend.label_text_font_size = '12pt'

    # Link x-axes
    p2.x_range = p1.x_range
    p3.x_range = p1.x_range

    # Build mosaic layout: time series on left, mask on right
    left_column = column(p1, p2, p3)

    if rio_topos is not None:
        mask = get_common_mask(rio_topos)
        p_mask = plot_common_mask(mask, rio_topos[0])
        right_column = p_mask
        layout = row(left_column, right_column)
    else:
        layout = left_column

    # Save plot
    html = outdir.joinpath('d_volume.html')
    output_file(html)
    print('\n --> %s \n' % html)
    save(layout)

    return

def plot_common_mask(mask, topo_ex, tile_choice = 'Esri'):

    # calculate transform to web mercator (EPSG:3857) and reprojected extent
    dst_crs, tform, width, height, left, bottom, right, top = calculate_tform_to_webmctor_and_reproj_extent(topo_ex)

    nodata = 1

    # Reproject mask to Web Mercator
    dst_data = np.empty((height, width), dtype=float)
    reproject(
        source=mask.astype(int),
        destination=dst_data,
        src_transform=topo_ex.transform,
        src_crs=topo_ex.crs,
        dst_transform=tform,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
        src_nodata=nodata,
        dst_nodata=np.nan,
    )

    mask = np.zeros((height, width), dtype=float)
    mask[dst_data == 0] = 255

    # Flip: rasterio stores top→bottom, Bokeh needs bottom→top
    img = np.flipud(mask)

    # Create figure in Web Mercator
    p = figure(
        x_axis_type="mercator",
        y_axis_type="mercator",
        width=600,
        height=750,
        title='AREA OF CALCULATION'
    )

    # Add OSM tile
    p.add_tile(osm_tile(tile_choice))

    # plot mask
    p.image(
        image=[img],
        x=left,
        y=bottom,
        dw=(right - left),
        dh=(top - bottom),
        palette=["rgba(0,0,0,0)", "rgba(255,0,0,0.4)"]
    )
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None

    return p

def parse_date(date_string):
    date = parser.parse(date_string)

    return date
