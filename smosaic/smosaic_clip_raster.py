import os
from pyproj import Transformer
import pyproj
import shapely
import rasterio
from rasterio.mask import mask as rasterio_mask
from smosaic.smosaic_utils import get_coverage_projection
from shapely.ops import transform

def clip_raster(input_raster_path, output_folder, clip_geometry, projection_output, output_filename=None):
    """
    Clip a raster using a Shapely geometry and save the result to another folder.
    
    Parameters:
    - input_raster_path: Path to the input raster file
    - output_folder: Folder where the clipped raster will be saved
    - clip_geometry: Shapely geometry object used for clipping
    - output_filename: Optional output filename (defaults to input filename with '_clipped' suffix)
    
    Returns:
    - Path to the saved clipped raster
    """

    if (projection_output=="BDC"):
        proj_bdc = get_coverage_projection()
        data_proj = proj_bdc
    else:
        data_proj = pyproj.CRS.from_epsg(projection_output)

    proj_converter = Transformer.from_crs(pyproj.CRS.from_epsg(4326), data_proj, always_xy=True).transform
    reproj_clip_geometry = transform(proj_converter, clip_geometry)
    
    os.makedirs(output_folder, exist_ok=True)
    
    if output_filename is None:
        base_name = os.path.basename(input_raster_path)
        name, ext = os.path.splitext(base_name)
        output_filename = f"{name}_clipped{ext}"
    
    output_path = os.path.join(output_folder, output_filename)
    
    with rasterio.open(input_raster_path) as src:
        out_image, out_transform = rasterio_mask (
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
