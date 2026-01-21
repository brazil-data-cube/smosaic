import os
import pyproj
import tqdm
import shapely
import rasterio
from pyproj import Transformer

from rasterio.mask import mask as rasterio_mask
from shapely.ops import transform

from smosaic.smosaic_utils import get_coverage_projection, load_jsons

def get_tiles_intersecting_tif(tif_path, grid_data):
    """
    Find which grid tiles intersect with a TIFF file's extent
    
    Args:
        tif_path (str): Path to the TIFF file
        geojson_path (str): Path to the GeoJSON grid file
    
    Returns:
        list: List of tile IDs that intersect with the TIFF extent
    """

    proj_bdc = get_coverage_projection()

    proj_converter = Transformer.from_crs(proj_bdc, pyproj.CRS.from_epsg(4326), always_xy=True).transform

    with rasterio.open(tif_path) as src:
        bounds = src.bounds
        tif_extent = shapely.geometry.box(bounds.left, bounds.bottom, bounds.right, bounds.top)
        reproj_tif_extent = transform(proj_converter, tif_extent)

    tiles = []
    
    for feature in grid_data['features']:
        grid_geom = shapely.geometry.shape(feature['geometry'])
        if reproj_tif_extent.intersects(grid_geom):
            tiles.append(feature['properties']['tile'])

    return tiles

def clip_from_grid(input_folder, grid):
    
    bdc_grids_data = load_jsons("grids")
    
    for g in bdc_grids_data['grids']:
        if (g['name'] == grid):
            selected_grid = g

    uncropped_tifs = [
        os.path.join(input_folder, f) for f in os.listdir(input_folder)
    ]

    tiles = get_tiles_intersecting_tif(uncropped_tifs[0], selected_grid)

    proj_bdc = get_coverage_projection()
    proj_converter = Transformer.from_crs(pyproj.CRS.from_epsg(4326), proj_bdc, always_xy=True).transform

    selected_tiles_reproj = []

    for t in tiles:
        for g in bdc_grids_data['grids']:
            if (g['name'] == grid):
                for tile in g['features']:
                    if tile['properties']['tile'] == t:
                        new_t = tile
                        geom = new_t['geometry']
                        shapely_geom = shapely.geometry.shape(geom)
                        reproj_geom = transform(proj_converter, shapely_geom)
                        new_t['geometry'] = shapely.geometry.mapping(reproj_geom)
                        selected_tiles_reproj.append(new_t)

    for image in uncropped_tifs:
        for tile in tqdm.tqdm(tiles, desc='Clipping... ', unit=" itens", total=len(tiles)):

            for t in selected_tiles_reproj:
                if (t['properties']['tile'] == tile):
                    selected_tile = t
            
            reproj_geom = selected_tile['geometry']
            
            base_name = os.path.basename(image)
            name, ext = os.path.splitext(base_name)
            output_filename = f"{name}_{tile}{ext}"
            
            output_path = os.path.join(input_folder, output_filename)
            
            with rasterio.open(image) as src:
                out_image, out_transform = rasterio_mask (
                    src, 
                    [reproj_geom], 
                    crop=True,
                    all_touched=True
                )
                
                out_meta = src.meta.copy()
                
                out_meta.update({
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform
                })
                
                with rasterio.open(output_path, "w", **out_meta) as dest:
                    dest.write(out_image)

    for f in uncropped_tifs:
        try:
            pass
            os.remove(f)
        except:
            pass