import os
import pyproj
import tqdm
import shapely
import rasterio
from pyproj import Transformer

from rasterio.mask import mask as rasterio_mask
from shapely.ops import transform

from smosaic.smosaic_utils import find_grid_by_name, get_coverage_projection, load_jsons

def filter_scenes(collection, data_dir, geom):
    """
    Filter and select specific scenes from a collection based on spatial criteria.
    
    Args:
        collection (str): BDC collection identifier (e.g., "S2_L2A-1").
        data_dir (str): Directory path where scene data is stored.
        clip_geometry (shapely.geometry): Spatial boundary for clipping.
    """
    if collection in ['S2_L2A-1','S2_L1C_BUNDLE-1']:
        grid_data = find_grid_by_name("MGRS")
    
    list_dir = [item for item in os.listdir(os.path.join(data_dir, collection))
                if os.path.isdir(os.path.join(data_dir, collection, item))]
    
    filtered_scenes = []
    
    for scene in list_dir:
        item = [item for item in grid_data["features"] if item["properties"]["name"] == scene]
        if item:
            grid_geom = shapely.geometry.shape(item[0]['geometry'])
            if geom.intersects(grid_geom):
                filtered_scenes.append(item[0]['properties']['name'])
    
    return filtered_scenes