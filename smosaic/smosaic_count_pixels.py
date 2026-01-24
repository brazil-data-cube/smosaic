import rasterio
from rasterio.mask import mask
import numpy as np
import shapely.geometry
from shapely.ops import transform
from pyproj import CRS, Transformer

from smosaic.smosaic_utils import get_coverage_projection

import rasterio
from rasterio.mask import mask
import numpy as np
from shapely.ops import transform
from pyproj import CRS, Transformer

def count_pixels(raster_path, target_values, geom):
    """
    Counts pixels matching target_values within the intersection of the raster and a geometry.
    
    Args:
        raster_path (str): Path to the raster file.
        target_values (list): List of pixel values to count.
        geom (shapely.geometry): Geometry object (e.g., Polygon) in EPSG:4326 (Lat/Lon).
        
    Returns:
        dict: 
            'total': Total count of valid pixels inside the geometry (including 0s).
            'count': Count of pixels matching target_values inside the geometry.
    """
    
    with rasterio.open(raster_path) as src:

        if src.crs and src.crs.to_epsg() != 4326:
            project = Transformer.from_crs(
                CRS.from_epsg(4326), 
                src.crs, 
                always_xy=True
            ).transform
            geom_transformed = transform(project, geom)
        else:
            geom_transformed = geom

        out_image, out_transform = mask(
            src, 
            [geom_transformed], 
            crop=True, 
            nodata=src.nodata
        )
        
        data = out_image[0] 

        if src.nodata is not None:
            is_inside_geom = (data != src.nodata) & (~np.isnan(data))
        else:
            is_inside_geom = ~np.isnan(data)

        target_mask = np.isin(data, target_values) & is_inside_geom
        count = target_mask.sum()
        
        total_valid_pixels = is_inside_geom.sum()
        
        return dict(total=int(total_valid_pixels), count=int(count))