import os
from osgeo import gdal
from smosaic.smosaic_utils import COVERAGE_PROJ

def reproject_tifs(sorted_data, cloud_sorted_data, data_dir, projection_output):
    
    images =  [item['file'] for item in sorted_data]
    cloud_images = [item['file'] for item in cloud_sorted_data]

    for i in range(0, len(images)):
        image_filename = images[i].split('/')[-1].split('.')[0]
        output_file = os.path.join(data_dir, f'{image_filename}_reprojected.tif')
        src_ds = gdal.Open(images[i])
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
            resampleAlg=gdal.GRA_NearestNeighbour,
            xRes=10,     
            yRes=-10      
        )
        
        gdal.Warp(output_file, src_ds, options=warp_options)
        src_ds = None
        sorted_data[i]['file'] = output_file
    
    for i in range(0, len(images)):
        image_filename = cloud_images[i].split('/')[-1].split('.')[0]
        output_file = os.path.join(data_dir, f'{image_filename}_reprojected.tif')
        src_ds = gdal.Open(cloud_images[i])
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
            resampleAlg=gdal.GRA_NearestNeighbour,
            xRes=10,      
            yRes=-10    
        )
        
        gdal.Warp(output_file, src_ds, options=warp_options)
        src_ds = None
        cloud_sorted_data[i]['file'] = output_file
    
    return dict(reprojected_images=sorted_data, reprojected_cloud_images=cloud_sorted_data)