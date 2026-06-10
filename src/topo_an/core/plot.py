import numpy as np
from dateutil import parser
from bokeh.models import (LinearColorMapper, Slider, CustomJS, ColorBar, Span, WMTSTileSource, RadioButtonGroup, Label,
                          Select, ColumnDataSource)
from bokeh.plotting import figure, save, output_file
from bokeh.layouts import column, row
from bokeh.io import curdoc
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

def parse_date(date_string):
    date = parser.parse(date_string)

    return date

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

def plot_topos(z, left, bottom, right, top, dates, low=-5, high=5, name=None, type='topo', width=1536, height=864,
               label=False, labels=None):

    # set title
    if type =='topo':
        title = 'BEACH HEIGHT'
        title_cbar = "Elevation (mIGN69)"
    elif type =='dtopo':
        title = 'BEACH HEIGHT DIFFERENCE'
        title_cbar = "Difference (m)"

    # set subtitle for each topo
    if isinstance(name, str):
        names = [name for i in range(len(z))]
    else:
        names = name
    subtitles = [dates[i] + ' ' + names[i] for i in range(len(dates))]

    # Create figure
    p = figure(title=subtitles[0], width=width, height=height, x_axis_type="mercator", y_axis_type="mercator",
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
    slider = Slider(start=0, end=len(z) - 1, step=1, value=0, title=title, format=" ", width=int(0.8 * width),
                    show_value=False)

    # stat label
    if label:
        dh = labels['dh']
        dv = labels['dv']
        # Fixed Label for the mean height stat (top-left corner of the plot)
        stat_label = Label(
            x=10, y=250,  # pixels from bottom-left (screen coords)
            x_units="screen", y_units="screen",
            text=f"dh: {dh[0]} m     dv: {dh[0]} m3",
            text_color="white", text_font_size="14px",
            background_fill_color="#185fa5", background_fill_alpha=0.75,
            border_line_color="white", padding=6,
        )
        p.add_layout(stat_label)
        label_js = 'label.text = "dh: " + dh[idx].toFixed(2) + " m"  + "     dv: "+ dv[idx].toFixed(0) + " m3"';

    else:
        stat_label = None
        label_js = ''
        dh = None
        dv = None

    code_js = """
            const idx = slider.value;
            img.data_source.data['image'][0] = arrays[idx];
            // Update the fixed Label text
            // label.text = "Mean height diff: " + dh[idx].toFixed(2) + " m";
            %s
            img.data_source.change.emit();
            p.title.text = `${titles[idx]}`;
        """%(label_js)
    callback = CustomJS(args=dict(img=img,
                                  arrays=z,
                                  slider=slider,
                                  label=stat_label,
                                  p=p,
                                  dh=dh,
                                  dv=dv,
                                  titles=subtitles), code=code_js)

    slider.js_on_change('value', callback)

    # Colour bar
    color_bar = ColorBar(color_mapper=color_mapper, width=16, location=(0, 0), title=title_cbar,
    title_text_font_size="12pt", title_text_font_style="bold")
    p.add_layout(color_bar, "right")

    layout = column(slider, p)

    return layout

def plot_dv(names, mean_h, t, t_ref, dh_with_ref, dv_with_ref, layout_dh):

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
    p1 = figure(width=900, height=210, x_axis_type='datetime', title='MEAN BEACH HEIGHT')
    p2 = figure(width=900, height=210, x_axis_type='datetime', title='MEAN HEIGHT DIFFERENCE WITH REF TOPO')
    p3 = figure(width=900, height=210, x_axis_type='datetime', title='VOLUME DIFFERENCE WITH REF TOPO')

    # Reference line (vertical) - same for all plots
    ref_line = Span(location=t_ref, dimension='height', line_color='aqua', line_width=3.5)
    p1.add_layout(ref_line)
    p2.add_layout(ref_line)
    p3.add_layout(ref_line)

    # Add ref_line to legend using dummy invisible lines
    p1.line([t_ref, t_ref], [mean_h.min(), mean_h.max()], color='aqua', line_width=3.5, legend_label='ref', alpha=1)

    # Wavecams data
    if len(inds_wcams) > 0:
        p1.scatter(t[inds_wcams], mean_h[inds_wcams], size=6, color='darkblue', marker='diamond', legend_label='wavecams')
        p1.line(t[inds_wcams], mean_h[inds_wcams], color='darkblue', line_width=2)
        p2.scatter(t[inds_wcams], dh_with_ref[inds_wcams], size=6, color='darkblue', marker='diamond', legend_label='wavecams')
        p2.line(t[inds_wcams], dh_with_ref[inds_wcams], color='darkblue', line_width=2)
        p3.scatter(t[inds_wcams], dv_with_ref[inds_wcams], size=6, color='darkblue', marker='diamond', legend_label='wavecams')
        p3.line(t[inds_wcams], dv_with_ref[inds_wcams], color='darkblue', line_width=2)

    # Sporadic data
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
    p3.yaxis.axis_label_text_color = 'black'

    # Grid and legend settings
    p1.grid.visible = True
    p2.grid.visible = True
    p3.grid.visible = True
    p1.legend.location = 'top_right'
    p1.legend.label_text_font_size = '8pt'
    p1.legend.background_fill_alpha = 0.7
    p2.legend.location = 'top_right'
    p2.legend.label_text_font_size = '8pt'
    p2.legend.background_fill_alpha = 0.7
    p3.legend.location = 'top_right'
    p3.legend.label_text_font_size = '8pt'
    p3.legend.background_fill_alpha = 0.7

    # Link x-axes
    p2.x_range = p1.x_range
    p3.x_range = p1.x_range

    # Build mosaic layout: time series on left, layout_dh on right
    left_column = column(p1, p2, p3)
    layout = row(left_column, layout_dh)

    return layout

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

    mask[mask == 0] = 1
    mask[mask==255] = 0
    return p, np.flipud(mask.astype(int))

def gather_analysis_layouts(layout_h, layout_dh, layout_dv, outdir, subdir, name_out):


    # output directory
    outdir = outdir.joinpath(subdir)
    outdir.mkdir(parents=True, exist_ok=True)

    radio = RadioButtonGroup(
        labels=["Beach Height", "Beach Height difference with ref", "Beach Volume difference with ref"],
        active=0,
        button_type="success"
    )
    layout_h.visible = True  # default, no need to set explicitly
    layout_dh.visible = False
    layout_dv.visible = False

    # Simple loop: show only the plot matching the active index
    callback = CustomJS(args=dict(plots=[layout_h, layout_dh, layout_dv]), code="""
            for (let i = 0; i < plots.length; i++) {
                plots[i].visible = (i === cb_obj.active);
            }
        """)
    radio.js_on_change("active", callback)

    layout = column(radio, layout_h, layout_dh, layout_dv, sizing_mode="stretch_both")
    output_file(outdir.joinpath(f'{name_out}.html'))
    print('\n --> %s \n' %(outdir.joinpath(f'{name_out}.html')))
    save(layout)
    return

def plot_validation(wc_topo, sp_topo, rmse, mae, corr, left, bottom, right, top):

    source = ColumnDataSource({"image": [wc_topo]})
    all_data = ColumnDataSource({"r1": [wc_topo], "r2": [sp_topo], "r3": [wc_topo - sp_topo]})

    p = figure(x_range=(left, left + (right - left)), y_range=(bottom, bottom + (top - bottom)),
               x_axis_type="mercator", y_axis_type="mercator", width=700, height=500)
    p.add_tile("Esri.WorldImagery")

    # Hide grid lines
    p.grid.visible = False

    # color mapper
    color_mapper_h = get_color_mapper(low=-5, high=5, type='topo')

    p.image(image="image", x=left, y=bottom, dw=(right - left), dh=(top - bottom),
            source=source, color_mapper=color_mapper_h, alpha=0.7)

    select = Select(title="Select raster", value="Raster 1",
                    options=["Raster 1", "Raster 2", "Raster 3"])

    callback = CustomJS(args=dict(source=source, all_data=all_data), code="""
        const map = {
            'Raster 1': all_data.data['r1'],
            'Raster 2': all_data.data['r2'],
            'Raster 3': all_data.data['r3'],
        };
        source.data['image'] = map[cb_obj.value];
        source.change.emit();
    """)
    select.js_on_change("value", callback)

    # show(column(select, p))
    layout = column(select, p)
    output_file('test_valid.html')
    save(layout)
