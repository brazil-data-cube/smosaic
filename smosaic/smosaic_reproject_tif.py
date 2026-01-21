import os
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import pyproj
import numpy as np

from smosaic.smosaic_utils import COVERAGE_PROJ

def reproject_tif(input_folder: str, input_filename: str):

    input_file = os.path.join(input_folder, f'{input_filename}.tif')
    output_file = os.path.join(input_folder, f'{input_filename}.tif')

    with rasterio.open(input_file) as src:
        transform, width, height = calculate_default_transform(
            src.crs,  
            COVERAGE_PROJ, 
            src.width,  
            src.height, 
            *src.bounds 
        )
        
        transform = rasterio.Affine(10, transform.b, transform.c,
                                   transform.d, -10, transform.f)
        
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': COVERAGE_PROJ,
            'transform': transform,
            'width': width,
            'height': height
        })
        
        with rasterio.open(output_file, 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=COVERAGE_PROJ,
                    resampling=Resampling.bilinear
                )
    