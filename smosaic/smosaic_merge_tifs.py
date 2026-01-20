import os
import pyproj
import shapely
import rasterio
import numpy as np

from shapely.ops import transform as shapely_transform
from rasterio.merge import merge as rasterio_merge
from rasterio.warp import calculate_default_transform, reproject, Resampling

from smosaic.smosaic_utils import clean_dir, get_all_cloud_configs, get_coverage_projection


def merge_tifs(tif_files, output_path, band, projection_output, path_row=None, extent=None):
    """
    Merge a list of TIFF files into one mosaic, reprojecting to EPSG:4326 or BDC PROJ.
    
    Parameters:
    -----------
    tif_files : list
        List of paths to input TIFF files
    output_path : str
        Path to save the merged output TIFF
    extent : tuple (optional)
        Bounding box for output in format (minx, miny, maxx, maxy) in EPSG:4326 or BDC PROJ.
        If None, will use the combined extent of all input files.
    """
    
    reprojected_files = []
    bounds = []

    cloud_dict = get_all_cloud_configs()
    cloud_bands = [item['cloud_band'] for item in cloud_dict.values()]

    if band in cloud_bands:
        nodata = next((config['no_data_value'] for config in cloud_dict.values() if config['cloud_band'] == band), None)
    else:
        nodata = 0 

    for tif in tif_files:
        with rasterio.open(tif) as src:

            profile = src.profile  
            left, bottom, right, top = src.bounds
            src_extent = shapely.geometry.box(left, bottom, right, top)

            profile['nodata'] = nodata

            if(projection_output=='BDC'):
                proj_bdc = get_coverage_projection()
                proj_converter = pyproj.Transformer.from_crs(
                    src.crs, 
                    proj_bdc, 
                    always_xy=True
                ).transform
                dst_crs = proj_bdc
            else:
                proj_converter = pyproj.Transformer.from_crs(
                    src.crs, 
                    'EPSG:'+str(projection_output), 
                    always_xy=True
                ).transform
                dst_crs = 'EPSG:'+str(projection_output)

            reproj_bbox = shapely_transform(proj_converter, src_extent)
            bounds.append(reproj_bbox.bounds)
            
            dst_transform, width, height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds
            )
            
            reproj_data = np.zeros((src.count, height, width), dtype=src.dtypes[0])

            reproject(
                source=rasterio.band(src, range(1, src.count + 1)),
                destination=reproj_data,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=Resampling.nearest,
                nodata=nodata
            )
            
            temp_path = f'temp_{os.path.basename(tif)}'
            reprojected_files.append(temp_path)

            with rasterio.open(
                temp_path,
                'w',
                driver='GTiff',
                height=height,
                width=width,
                count=src.count,
                dtype=reproj_data.dtype,
                crs=dst_crs,
                transform=dst_transform,
                nodata=nodata
            ) as dst:
                dst.write(reproj_data)
    
    if extent is None:
        minx = min(b[0] for b in bounds)
        miny = min(b[1] for b in bounds)
        maxx = max(b[2] for b in bounds)
        maxy = max(b[3] for b in bounds)
        extent = (minx, miny, maxx, maxy)
    else:
        minx, miny, maxx, maxy = extent
    
    src_files_to_mosaic = []
    for f in reprojected_files:
        src = rasterio.open(f)
        src_files_to_mosaic.append(src)
    
    mosaic, out_trans = rasterio_merge(src_files_to_mosaic, bounds=extent)
    
    out_meta = src.meta.copy()
    out_meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_trans,
        "crs": dst_crs,
        "nodata": nodata
    })
    
    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(mosaic)

    for src in src_files_to_mosaic:
        src.close()

    return output_path
