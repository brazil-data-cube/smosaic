import os
import rasterio
import datetime

import numpy as np

from rasterio.warp import Resampling

from smosaic.smosaic_get_dataset_extents import get_dataset_extents
from smosaic.smosaic_merge_tifs import merge_tifs
from smosaic.smosaic_utils import days_from_new_year, get_all_cloud_configs


def merge_scene(sorted_data, cloud_sorted_data, scenes, collection_name, band, data_dir):

    merge_files = []
    provenance_merge_files = []
    
    for scene in scenes:

        images =  [item['file'] for item in sorted_data if item.get("scene") == scene]
        cloud_images = [item['file'] for item in cloud_sorted_data if item.get("scene") == scene]
        
        temp_images = []
        provenance_images = []

        for i in range(0, len(images)):

            with rasterio.open(images[i]) as src:
                image_data = src.read()  
                profile = src.profile  
                height, width = src.shape  

            with rasterio.open(cloud_images[i]) as mask_src:
                cloud_mask = mask_src.read(1) 
                cloud_mask = mask_src.read(
                    1,  
                    out_shape=(height, width), 
                    resampling=Resampling.nearest  
                )
            
            cloud_dict = get_all_cloud_configs()
            clear_mask = np.isin(cloud_mask, cloud_dict[collection_name]['non_cloud_values'])

            if 'nodata' not in profile or profile['nodata'] is None:
                profile['nodata'] = 0  

            masked_image = np.full_like(image_data, profile['nodata'])
            masked_image[:, clear_mask] = image_data[:, clear_mask]  
            datatime_image = datetime.datetime.strptime(images[i].split('/')[-1].split("_")[2].split('T')[0], "%Y%m%d")
            year, days = days_from_new_year(datatime_image)

            provenance = np.full_like(masked_image, profile['nodata'])
            
            valid_mask = masked_image != profile['nodata']
            provenance[valid_mask] = days
    
            for band_idx in range(image_data.shape[0]):
                masked_image[band_idx, clear_mask] = image_data[band_idx, clear_mask]

            file_name = 'clear_' + images[i].split('/')[-1]
            temp_images.append(os.path.join(data_dir, file_name))

            provenance_file_name = 'provenance_' + images[i].split('/')[-1]
            provenance_images.append(os.path.join(data_dir, provenance_file_name))

            with rasterio.open(os.path.join(data_dir, file_name), 'w', **profile) as dst:
                dst.write(masked_image)
            
            with rasterio.open(os.path.join(data_dir, provenance_file_name), 'w', **profile) as dst:
                dst.write(provenance)

        temp_images.append(images[0])
        provenance_images.append(provenance_images[0])

        output_file = os.path.join(data_dir, "merge_"+collection_name.split('-')[0]+"_"+scene+"_"+band+".tif")  

        provenance_output_file = os.path.join(data_dir, "provenance_merge_"+collection_name.split('-')[0]+"_"+scene+"_"+band+".tif")  

        datasets = [rasterio.open(file) for file in temp_images]  
        
        extents = get_dataset_extents(datasets)

        merge_tifs(tif_files=temp_images, output_path=output_file, band=band, path_row=scene, extent=extents)
        
        merge_tifs(tif_files=provenance_images, output_path=provenance_output_file, band=band, path_row=scene, extent=extents)

        merge_files.append(output_file)
        provenance_merge_files.append(provenance_output_file)

        for f in temp_images:
            try:
                os.remove(f)
            except:
                pass

    return merge_files
