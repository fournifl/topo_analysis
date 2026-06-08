import numpy as np
from bokeh.models import LinearColorMapper, Slider, CustomJS, ColorBar
from bokeh.plotting import figure, save, output_file
from bokeh.layouts import column
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import to_hex
from rasterio.warp import reproject, Resampling

from topo_an.core.geo_utils import osm_tile, calculate_tform_to_webmctor_and_reproj_extent


def convert_mpl_colormap_to_hex(cmap, n_colors):

    # Generate colors from the colormap (e.g., 256 colors)
    colors_rgb = cmap(np.linspace(0, 1, n_colors))

    # Convert RGB values (0-1 range) to hex strings
    palette = [to_hex(rgb) for rgb in colors_rgb]

    return palette

def get_color_mapper(low=-5, high=5):
    # customized colormap, # Edit this gradient at
    # https://eltos.github.io/gradient/#0C0A69-2A5FD9-00E55A-FBFF03-F2B513-8B6316-371B00
    cmap = LinearSegmentedColormap.from_list('my gradient', (
        (0.000, (0.047, 0.039, 0.412)),
        (0.167, (0.165, 0.373, 0.851)),
        (0.333, (0.000, 0.898, 0.353)),
        (0.500, (0.984, 1.000, 0.012)),
        (0.667, (0.949, 0.710, 0.075)),
        (0.833, (0.545, 0.388, 0.086)),
        (1.000, (0.216, 0.106, 0.000))))
    palette = convert_mpl_colormap_to_hex(cmap, 256)

    # Setup color mapper
    color_mapper = LinearColorMapper(palette=palette, low=low, high=high)
    color_mapper.nan_color = (0, 0, 0, 0)

    return color_mapper

def plot_topos(src_topos, dates, output_dir, name_out, tile_choice ='Esri', low=-5, high=5, name=None):

    z = []

    # output directory
    outdir = output_dir.joinpath('plots')
    outdir.mkdir(parents=True, exist_ok=True)

    if isinstance(name, str):
        names = [name for i in range(len(src_topos))]
    else:
        names = name

    titles = [dates[i] + ' ' + names[i] for i in range(len(dates))]

    # calculate transform to web mercator (EPSG:3857) and reprojected extent
    dst_crs, tform, width, height, left, bottom, right, top = calculate_tform_to_webmctor_and_reproj_extent(src_topos[0])

    for i, src in enumerate(src_topos):

        # read topo data
        src_data = src.read(1).astype(float)  # band 1
        nodata = src.nodata

        # Reproject topo to Web Mercator
        dst_data = np.empty((height, width), dtype=np.float32)
        reproject(
            source=src_data,
            destination=dst_data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=tform,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear,
            src_nodata=nodata,
            dst_nodata=np.nan,
        )


        # Mask nodata
        if nodata is not None:
            dst_data[dst_data == nodata] = np.nan

        # Flip: rasterio stores top→bottom, Bokeh needs bottom→top
        img = np.flipud(dst_data)
        z.append(img)

    # Create figure
    p = figure(title=titles[0], width=1536, height=864, x_axis_type="mercator",
               y_axis_type="mercator",
               match_aspect=True)

    # Add OSM tiles
    p.add_tile(osm_tile(tile_choice))

    # Hide grid lines
    p.grid.visible = False

    # color mapper
    color_mapper = get_color_mapper(low=low, high=high)

    # plot topo
    img = p.image(image=[z[0]], x=left, y=bottom, dw=(right - left), dh=(top - bottom), color_mapper=color_mapper)

    # Create slider with CustomJS callback
    slider = Slider(start=0, end=len(z) - 1, step=1, value=0, title=f"INTERTIDAL TOPOGRAPHY", format=" ", width=1200,
                    show_value=False)

    callback = CustomJS(args=dict(img=img,
                                  arrays=z,
                                  slider=slider,
                                  p=p,
                                  titles=titles), code="""
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

    # Save plot to html
    output_file(outdir.joinpath(f'{name_out}.html'))
    layout = column(slider, p)
    save(layout)

    return

