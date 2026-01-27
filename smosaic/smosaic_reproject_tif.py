import os
from osgeo import gdal
from smosaic.smosaic_utils import COVERAGE_PROJ

def reproject_tif(input_folder: str, input_filename: str, projection_output: str):
    
    input_file = os.path.join(input_folder, f'{input_filename}.tif')
    
    output_file = os.path.join(input_folder, f'{input_filename}.tif')
    
    src_ds = gdal.Open(input_file)
    if src_ds is None:
        raise FileNotFoundError(f"Could not open file: {input_file}")

    src_nodata = src_ds.GetRasterBand(1).GetNoDataValue()
    
    if projection_output == "BDC":
        dst_crs = COVERAGE_PROJ
    else:
        dst_crs = f"EPSG:{projection_output}"

    warp_options = gdal.WarpOptions(
        format='GTiff',
        dstSRS=dst_crs,
        srcNodata=src_nodata,
        dstNodata=src_nodata,
        resampleAlg=gdal.GRA_NearestNeighbour
    )
    
    gdal.Warp(output_file, src_ds, options=warp_options)
    
    src_ds = None
    
    return output_file