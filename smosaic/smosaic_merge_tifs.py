import os
import sys
import subprocess
from osgeo import gdal

try:
    from osgeo_utils import gdal_merge as gm
    gm_available = True
except ImportError:
    gm_available = False

from smosaic.smosaic_utils import get_all_cloud_configs

def merge_tifs(tif_files, output_path, band, path_row=None, extent=None):
    """Merge multiple TIFF files into a single TIFF file."""
    
    cloud_dict = get_all_cloud_configs()
    if any(config['cloud_band'] == band for config in cloud_dict.values()):
        nodata = next((config['no_data_value'] for config in cloud_dict.values() 
                      if config['cloud_band'] == band), None)
    else:
        nodata = 0 

    src_ds = gdal.Open(tif_files[0])
    dt = src_ds.GetRasterBand(1).DataType
    dtype_name = gdal.GetDataTypeName(dt)
    src_ds = None

    merge_args = ['', '-q', '-ot', dtype_name, '-of', 'GTiff', '-o', output_path]
    
    if nodata is not None:
        merge_args.extend(['-n', str(nodata), '-a_nodata', str(nodata)])
    
    if gm_available:
        merge_args.extend(tif_files)
        gm.main(merge_args)
            
    else:
        cmd = ['gdal_merge.py'] + merge_args[1:] + tif_files

        with open(os.devnull, 'w') as devnull:
            subprocess.run(cmd, stdout=devnull, stderr=devnull, check=True)

    return output_path