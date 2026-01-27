import os
import rasterio
from rasterio.mask import mask as rasterio_mask
import pyproj
from pyproj import Transformer
from shapely.ops import transform
import shapely


def clip_raster(input_raster_path, output_folder, clip_geometry, output_filename=None):
    
    with rasterio.open(input_raster_path) as src:
        
        data_crs = src.crs
        
        proj_converter = Transformer.from_crs(
            pyproj.CRS.from_epsg(4326), 
            data_crs, 
            always_xy=True
        ).transform
        
        reproj_clip_geometry = transform(proj_converter, clip_geometry)
        
        os.makedirs(output_folder, exist_ok=True)
        
        if output_filename is None:
            base_name = os.path.basename(input_raster_path)
            name, ext = os.path.splitext(base_name)
            output_filename = f"{name}{ext}"
        
        output_path = os.path.join(output_folder, output_filename)
        
        out_image, out_transform = rasterio_mask(
            src, 
            [shapely.geometry.mapping(reproj_clip_geometry)],  
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
            
    os.remove(input_raster_path)
    return output_path