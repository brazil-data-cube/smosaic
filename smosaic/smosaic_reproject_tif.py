import os
import pyproj
from osgeo import gdal
from smosaic.smosaic_utils import COVERAGE_PROJ

def reproject_tifs(sorted_data, cloud_sorted_data, data_dir, projection_output):
    
    images =  [item['file'] for item in sorted_data]
    cloud_images = [item['file'] for item in cloud_sorted_data]

    if projection_output == "BDC":
        x_res, y_res = 10, -10
    else:
        x_res, y_res = None, None

    for i in range(0, len(images)):
        image_filename = images[i].split('/')[-1].split('.')[0]
        output_file = os.path.join(data_dir, f'{image_filename}_reprojected.tif')
        src_ds = gdal.Open(images[i])
        src_nodata = src_ds.GetRasterBand(1).GetNoDataValue()
        
        if projection_output == "BDC":
            dst_wkt = COVERAGE_PROJ
        else:
            dst_crs = pyproj.CRS.from_epsg(projection_output)
            dst_wkt = dst_crs.to_wkt()

        warp_options = gdal.WarpOptions(
            format='GTiff',
            dstSRS=dst_wkt,
            srcNodata=src_nodata,
            dstNodata=src_nodata,
            resampleAlg=gdal.GRA_NearestNeighbour,
            xRes=x_res,     
            yRes=y_res      
        )
        
        gdal.Warp(output_file, src_ds, options=warp_options)
        src_ds = None
        sorted_data[i]['file'] = output_file
    
    for i in range(0, len(cloud_images)):
        image_filename = cloud_images[i].split('/')[-1].split('.')[0]
        output_file = os.path.join(data_dir, f'{image_filename}_reprojected.tif')
        src_ds = gdal.Open(cloud_images[i])
        src_nodata = src_ds.GetRasterBand(1).GetNoDataValue()
        
        if projection_output == "BDC":
            dst_wkt = COVERAGE_PROJ
        else:
            dst_crs = pyproj.CRS.from_epsg(projection_output)
            dst_wkt = dst_crs.to_wkt()

        warp_options = gdal.WarpOptions(
            format='GTiff',
            dstSRS=dst_wkt,
            srcNodata=src_nodata,
            dstNodata=src_nodata,
            resampleAlg=gdal.GRA_NearestNeighbour,
            xRes=x_res,      
            yRes=y_res    
        )
        
        gdal.Warp(output_file, src_ds, options=warp_options)
        src_ds = None
        cloud_sorted_data[i]['file'] = output_file
    
    return dict(reprojected_images=sorted_data, reprojected_cloud_images=cloud_sorted_data)