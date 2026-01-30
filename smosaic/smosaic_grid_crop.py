import os
import pyproj
import tqdm
import shapely
import rasterio
from pyproj import Transformer

from rasterio.mask import mask as rasterio_mask
from shapely.ops import transform

from smosaic.smosaic_clip_raster import clip_raster
from smosaic.smosaic_utils import COVERAGE_PROJ, get_coverage_projection, load_jsons


import rasterio
import shapely.geometry
import shapely.ops
import pyproj
from pyproj import Transformer

def get_tiles_intersecting_tif(tif_path, grid, projection_output):
    """
    Identifies tiles from a grid definition that intersect with a GeoTIFF.
    """
    
    grid_data = None
    grid_crs = None

    if projection_output == "BDC" and grid == "BDC_SM_V2":
        grid_data = load_jsons("BDC_SM_V2")
        grid_crs = COVERAGE_PROJ
    else:
        bdc_grids_data = load_jsons("grids")
        for g in bdc_grids_data['grids']:
            if g['name'] == grid:
                grid_data = g
                grid_crs = pyproj.CRS.from_epsg(4326) 
                break

    with rasterio.open(tif_path) as src:
        tif_crs = src.crs
        bounds = src.bounds
        tif_geom = shapely.geometry.box(bounds.left, bounds.bottom, bounds.right, bounds.top)
    if tif_crs != grid_crs:
        project = Transformer.from_crs(tif_crs, grid_crs, always_xy=True).transform
        search_geom = shapely.ops.transform(project, tif_geom)
    else:
        search_geom = tif_geom

    tiles = []
    
    features = grid_data.get('features', [])
    
    for feature in features:
        grid_geom = shapely.geometry.shape(feature['geometry'])
        
        if search_geom.intersects(grid_geom):
            tile_id = feature['properties'].get('tile')
            if tile_id:
                tiles.append(tile_id)

    return tiles

def clip_from_grid(input_folder, grid, tile_id, projection_output):
    """
    Clip images in input_folder according to grid and tile specifications
    
    Args:
        input_folder (str): Folder containing input TIFF files
        grid (str): Grid name
        tile_id (str): Tile ID (if None, find intersecting tiles)
    """
    
    uncropped_tifs = [
        os.path.join(input_folder, f) for f in os.listdir(input_folder)
        if f.lower().endswith(('.tif'))
    ]
    
    tiles = get_tiles_intersecting_tif(uncropped_tifs[0], grid)
    
    for image in uncropped_tifs:

        for tile in tiles:
        
            base_name = os.path.basename(image)
            name, ext = os.path.splitext(base_name)
            output_filename = f"{name}_{tile}{ext}"
            
            clip_raster(
                input_raster_path=image,
                output_folder=input_folder,
                projection_output=projection_output,
                output_filename=output_filename,
                grid=grid,
                tile_id=tile
            )