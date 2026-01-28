import os
import numpy as np
import rasterio
from rasterio.mask import mask as rasterio_mask
from rasterio.warp import reproject, Resampling, calculate_default_transform
import pyproj
from pyproj import Transformer
from shapely.ops import transform
import shapely
from shapely.geometry import box

from smosaic.smosaic_utils import COVERAGE_PROJ, load_jsons


def clip_raster(input_raster_path, output_folder, clip_geometry, projection_output, output_filename=None, grid=None, tile_id=None):
    
    using_grid = False
    if grid and tile_id:
        if grid == "BDC_SM_V2":
            bdc_grid_sm = load_jsons("BDC_SM_V2") 
            for feature in bdc_grid_sm['features']:
                if feature['properties']['tile'] == tile_id:
                    grid_geom = shapely.geometry.shape(feature['geometry'])
                    clip_geometry = grid_geom
                    using_grid = True
                    break

    if projection_output == "BDC":
        target_crs = COVERAGE_PROJ
    else:
        target_crs = pyproj.CRS.from_epsg(projection_output)

    with rasterio.open(input_raster_path) as src:
        
        if not using_grid:
            proj_converter = Transformer.from_crs(
                pyproj.CRS.from_epsg(4326), 
                src.crs,
                always_xy=True
            ).transform
            clip_geometry = transform(proj_converter, clip_geometry)
            
        out_image, out_transform = rasterio_mask(
            src, 
            [shapely.geometry.mapping(clip_geometry)],  
            crop=True,
            all_touched=True
        )

        if using_grid:

            bounds = clip_geometry.bounds 
            
            pixel_size_x = 10
            pixel_size_y = -10
            
            width = int((bounds[2] - bounds[0]) / pixel_size_x)
            height = int((bounds[3] - bounds[1]) / abs(pixel_size_y))
            
            target_transform = rasterio.transform.from_origin(
                bounds[0],
                bounds[3],
                pixel_size_x,
                abs(pixel_size_y)
            )
            
            resampled_data = np.zeros((out_image.shape[0], height, width), 
                                     dtype=out_image.dtype)
            
            reproject(
                source=out_image,
                destination=resampled_data,
                src_transform=out_transform,
                src_crs=src.crs, 
                dst_transform=target_transform,
                dst_crs=src.crs,  
                resampling=Resampling.nearest
            )
            
            output_data = resampled_data
            output_transform = target_transform
            output_width = width
            output_height = height
            output_crs = src.crs  
            
        else:

            if src.crs != target_crs:
                target_transform, target_width, target_height = calculate_default_transform(
                    src.crs, target_crs, 
                    out_image.shape[2], out_image.shape[1],
                    *clip_geometry.bounds
                )
                
                reprojected_data = np.zeros((out_image.shape[0], target_height, target_width), 
                                           dtype=out_image.dtype)
                
                reproject(
                    source=out_image,
                    destination=reprojected_data,
                    src_transform=out_transform,
                    src_crs=src.crs,
                    dst_transform=target_transform,
                    dst_crs=target_crs,
                    resampling=Resampling.nearest
                )
                
                output_data = reprojected_data
                output_transform = target_transform
                output_width = target_width
                output_height = target_height
                output_crs = target_crs
            else:
                output_data = out_image
                output_transform = out_transform
                output_width = out_image.shape[2]
                output_height = out_image.shape[1]
                output_crs = src.crs
        
        os.makedirs(output_folder, exist_ok=True)
        
        output_path = os.path.join(output_folder, output_filename)
        
        out_meta = src.meta.copy()
        out_meta.update({
            "height": output_height,
            "width": output_width,
            "transform": output_transform,
            "crs": output_crs
        })
        
        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(output_data)
    
    os.remove(input_raster_path)
    return output_path