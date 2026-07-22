import numpy as np
from dateutil import parser
from bokeh.models import (LinearColorMapper, Slider, CustomJS, ColorBar, Span, WMTSTileSource, RadioButtonGroup, Label,
                          Select, ColumnDataSource)
from bokeh.plotting import figure, save, output_file
from bokeh.layouts import column, row, gridplot
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import to_hex
from rasterio.warp import reproject, Resampling
from topo_an.core.geo_utils import calculate_tform_and_reproj_extent, get_common_mask


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

    if type == 'topo' or type =='topo_ref':
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
    elif type == 'topo_ref':
        title = 'REFERENCE BEACH HEIGHT'
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

    # Colour bar
    color_bar = ColorBar(color_mapper=color_mapper, width=16, location=(0, 0), title=title_cbar,
                         title_text_font_size="12pt", title_text_font_style="bold")
    p.add_layout(color_bar, "right")

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

    if len(z) > 1:
        # Create slider with CustomJS callback
        slider = Slider(start=0, end=len(z) - 1, step=1, value=0, title=title, format=" ", width=int(0.8 * width),
                        show_value=False)
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
        layout = column(slider, p)

    else:
        layout = p

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
    p1.line([t_ref, t_ref], [mean_h.min(), mean_h.max()], color='aqua', line_width=3.5, legend_label='t ref', alpha=0.7)

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
    dst_crs, tform, width, height, left, bottom, right, top = calculate_tform_and_reproj_extent(topo_ex)

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

def gather_analysis_layouts(layout_h, layout_h_ref, layout_dh, layout_dv, outdir, subdir, name_out):


    # output directory
    outdir = outdir.joinpath(subdir)
    outdir.mkdir(parents=True, exist_ok=True)

    radio = RadioButtonGroup(
        labels=["Beach Height", "Beach Height ref","Beach Height difference with ref", "Beach Volume difference with ref"],
        active=0,
        button_type="success"
    )
    layout_h.visible = True
    layout_h_ref.visible = False
    layout_dh.visible = False
    layout_dv.visible = False

    # Simple loop: show only the plot matching the active index
    callback = CustomJS(args=dict(plots=[layout_h, layout_h_ref, layout_dh, layout_dv]), code="""
            for (let i = 0; i < plots.length; i++) {
                plots[i].visible = (i === cb_obj.active);
            }
        """)
    radio.js_on_change("active", callback)

    layout = column(radio, layout_h, layout_h_ref, layout_dh, layout_dv, sizing_mode="stretch_both")
    output_file(outdir.joinpath(f'{name_out}.html'))
    print('\n --> %s \n' %(outdir.joinpath(f'{name_out}.html')))
    save(layout)
    return

def plot_validation_raster(wc_topo, sp_topo, rmse, mae, left, bottom, right, top, i):

    # create d_topo
    d_topo = wc_topo - sp_topo

    # initialize source variable to wcams topo
    source = ColumnDataSource({"image": [d_topo]})

    # gather all rasters in a ColumnDataSource object
    all_data = ColumnDataSource({"r1": [d_topo], "r2": [wc_topo], "r3": [sp_topo]})

    # create figure
    dw = right - left
    dh = top - bottom
    p = figure(
        x_range=(left, left + dw),
        y_range=(bottom, bottom + dh),
        x_axis_type="mercator", y_axis_type="mercator",
        width=800, height=550,
        title="Validation of Wavecams intertidal topography"
    )

    # add osm tile
    p.add_tile("Esri.WorldImagery")

    # Hide grid lines
    p.grid.visible = False

    # color mapper (one mapper per raster)
    mapper_1 = get_color_mapper(low=-1, high=1, type='dtopo')
    mapper_2 = get_color_mapper(low=-5, high=5, type='topo')
    mapper_3 = get_color_mapper(low=-5, high=5, type='topo')

    # plot raster
    p.image(
        image="image", x=left, y=bottom, dw=dw, dh=dh, source=source, color_mapper=mapper_1, alpha=0.7
    )

    # color bar
    color_bar = ColorBar(color_mapper=mapper_1, width=12, location=(0, 0))
    p.add_layout(color_bar, "right")

    # labels
    label_mae = Label(
        x=10, y=250, x_units="screen", y_units="screen",
        text=f"mae: {mae:.2f} m", text_color="white", text_font_size="14px",
        background_fill_color="#185fa5", background_fill_alpha=0.75, border_line_color="white", padding=6, visible=True
    )
    p.add_layout(label_mae)

    label_rmse = Label(
        x=10, y=215, x_units="screen", y_units="screen",
        text=f"rmse: {rmse:.2f} m", text_color="white", text_font_size="14px",
        background_fill_color="#185fa5", background_fill_alpha=0.75, border_line_color="white", padding=6, visible=True
    )
    p.add_layout(label_rmse)

    label_mean = Label(
        x=10, y=180, x_units="screen", y_units="screen",
        text=f"mean: {np.nanmean(d_topo):.2f} m", text_color="white", text_font_size="14px",
        background_fill_color="#185fa5", background_fill_alpha=0.75, border_line_color="white", padding=6, visible=True
    )
    p.add_layout(label_mean)

    label_median = Label(
        x=10, y=145, x_units="screen", y_units="screen",
        text=f"median: {np.nanmedian(d_topo):.2f} m", text_color="white", text_font_size="14px",
        background_fill_color="#185fa5", background_fill_alpha=0.75, border_line_color="white", padding=6, visible=True
    )
    p.add_layout(label_median)

    select = Select(
        title="Select raster",
        value="Difference",
        options=["Difference", "Wavecams", "Groundtruth" ]
    )

    configs = {
        "Difference": {"palette": mapper_1.palette, "low": mapper_1.low, "high": mapper_1.high},
        "Wavecams": {"palette": mapper_2.palette, "low": mapper_2.low, "high": mapper_2.high},
        "Groundtruth": {"palette": mapper_3.palette, "low": mapper_3.low, "high": mapper_3.high},
    }

    # javascript callback
    callback = CustomJS(
        args=dict(
            source=source,
            all_data=all_data,
            mapper=mapper_1,
            configs=configs,
            label_rmse=label_rmse,
            label_mae=label_mae,
            label_mean=label_mean,
            label_median=label_median
        ),
        code="""
        const raster_map = {
            'Difference': {data: all_data.data['r1'], ...configs['Difference']},
            'Wavecams': {data: all_data.data['r2'], ...configs['Wavecams']},
            'Groundtruth': {data: all_data.data['r3'], ...configs['Groundtruth']},
            
        };
        const chosen = raster_map[cb_obj.value];

        source.data['image'] = chosen.data;
        source.change.emit();

        mapper.palette = chosen.palette;
        mapper.low     = chosen.low;
        mapper.high    = chosen.high;
        
        label_rmse.visible = (cb_obj.value === 'Difference');
        label_mae.visible = (cb_obj.value === 'Difference');
        label_mean.visible = (cb_obj.value === 'Difference');
        label_median.visible = (cb_obj.value === 'Difference');
    """
    )
    select.js_on_change("value", callback)

    layout = column(select, p)

    return layout

def plot_validation(wc_topo, sp_topo, rmse, mae, corr, left, bottom, right, top, i):

    layout_validation_raster = plot_validation_raster(wc_topo, sp_topo, rmse, mae, left, bottom, right, top, i)

    mask = np.logical_or(np.isnan(wc_topo), np.isnan(sp_topo))
    wc_topo = np.ma.array(wc_topo, mask=mask).compressed().flatten()
    sp_topo = np.ma.array(sp_topo, mask=mask).compressed().flatten()

    error = wc_topo - sp_topo

    # ── 1. Scatter plot ──────────────────────────────────────
    p1 = figure(
        title="Wavecams vs Groundtruth",
        x_axis_label="Groundtruth",
        y_axis_label="Wavecams",
        width=400, height=350,
    )

    p1.scatter(
        x=sp_topo, y=wc_topo,
        size=3, alpha=0.5,
        color="#378ADD", line_color="white", line_width=0.5,
    )
    # 1:1 reference line
    lim = [sp_topo.min(), sp_topo.max()]
    # labels
    p1.line(lim, lim, line_dash="dashed", line_color="black", line_width=1.5)
    label_corr = Label(
        x=10, y=245, x_units="screen", y_units="screen",
        text=f"R2: {corr:.2f}", text_color="white", text_font_size="14px",
        background_fill_color="#185fa5", background_fill_alpha=0.75, border_line_color="white", padding=6, visible=True
    )
    p1.add_layout(label_corr)

    # ── 2. Box plot ──────────────────────────────────────────
    # Compute box stats for both arrays
    def box_stats(arr, label):
        q1, median, q3 = np.percentile(arr, [25, 50, 75])
        iqr = q3 - q1
        upper = min(arr.max(), q3 + 1.5 * iqr)
        lower = max(arr.min(), q1 - 1.5 * iqr)
        return dict(label=label, q1=q1, q2=median, q3=q3,
                    upper=upper, lower=lower)

    stats = [box_stats(error, 'error')]

    labels = [s["label"] for s in stats]
    src = ColumnDataSource(dict(
        x=labels,
        q1=[s["q1"] for s in stats],
        q2=[s["q2"] for s in stats],
        q3=[s["q3"] for s in stats],
        upper=[s["upper"] for s in stats],
        lower=[s["lower"] for s in stats],
        color=["#1D9E75"],
    ))

    p2 = figure(
        title="Distribution of the error",
        x_range=labels,
        y_axis_label="Value (m)",
        width=400, height=350,
    )

    # IQR box
    p2.vbar(x="x", top="q3", bottom="q1", width=0.5,
            source=src, alpha=0.6)
    # Whiskers
    p2.segment("x", "upper", "x", "q3", source=src, line_color="black")
    p2.segment("x", "lower", "x", "q1", source=src, line_color="black")
    # Whisker caps
    p2.rect("x", "upper", 0.2, 0.0001, source=src, line_color="black")
    p2.rect("x", "lower", 0.2, 0.0001, source=src, line_color="black")
    # Median line
    p2.rect("x", "q2", 0.5, 0.0001, source=src,
            line_color="white", line_width=2)

    # ── 3. Error histogram ───────────────────────────────────
    hist, edges = np.histogram(error, bins=30)

    p3 = figure(
        title="Error histogram  (wavecams − groundtruth)",
        x_axis_label="Error (m)",
        y_axis_label="Count",
        width=820, height=300,
    )
    p3.quad(
        top=hist, bottom=0,
        left=edges[:-1], right=edges[1:],
        fill_color="#378ADD", line_color="white", alpha=0.8,
    )
    # Zero-error reference
    p3.line([0, 0], [0, hist.max()],
            line_dash="dashed", line_color="#444441", line_width=1.5)

    layout_stats = row(p1, p2)
    layout_stats = column(layout_stats, p3)
    layout = row(layout_validation_raster, layout_stats)

    return layout

def gather_validation_layouts(layouts_val, outdir):

    labels = ['Validation %s' % i for i in range(len(layouts_val))]

    # --- Radio button group ---
    radio = RadioButtonGroup(
        labels=labels,
        active=0,
        button_type="success"
    )

    # Set initial visibility: only the first layout is visible
    for i, layout in enumerate(layouts_val):
        layout.visible = (i == 0)

    # Simple loop: show only the plot matching the active index
    callback = CustomJS(args=dict(plots=layouts_val), code="""
            for (let i = 0; i < plots.length; i++) {
                plots[i].visible = (i === cb_obj.active);
            }
        """)
    radio.js_on_change("active", callback)

    layout = column(radio, *layouts_val)

    output_file(outdir.joinpath('validation.html'))
    print('\n --> %s \n' % (outdir.joinpath('validation.html')))
    save(layout)
    return






