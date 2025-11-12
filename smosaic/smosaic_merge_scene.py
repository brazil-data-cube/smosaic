import os
import tqdm
import rasterio
import datetime

import numpy as np

from rasterio.warp import Resampling

from smosaic.smosaic_get_dataset_extents import get_dataset_extents
from smosaic.smosaic_merge_tifs import merge_tifs
from smosaic.smosaic_utils import days_from_new_year, get_all_cloud_configs


def merge_scene(sorted_data, cloud_sorted_data, scenes, collection_name, band, data_dir):

    merge_files = []
    
    for scene in scenes:

        images =  [item['file'] for item in sorted_data if item.get("scene") == scene]
        cloud_images = [item['file'] for item in cloud_sorted_data if item.get("scene") == scene]
        
        temp_images = []

        for i in tqdm.tqdm(range(0, len(images)), desc="Processing..."):

            try:
                with rasterio.open(images[i]) as src:
                    image_data = src.read()  
                    profile = src.profile  
                    height, width = src.shape  
            except rasterio.errors.RasterioIOError as e:
                continue

            try:
                with rasterio.open(cloud_images[i]) as mask_src:
                    cloud_mask = mask_src.read(1) 
                    cloud_mask = mask_src.read(
                        1,  
                        out_shape=(height, width), 
                        resampling=Resampling.nearest  
                    )
            except rasterio.errors.RasterioIOError as e:
                continue
            
            cloud_dict = get_all_cloud_configs()
            clear_mask = np.isin(cloud_mask, cloud_dict[collection_name]['non_cloud_values'])

            if 'nodata' not in profile or profile['nodata'] is None:
                profile['nodata'] = 0  

            masked_image = np.full_like(image_data, profile['nodata'])
            masked_image[:, clear_mask] = image_data[:, clear_mask]  

            for band_idx in range(image_data.shape[0]):
                masked_image[band_idx, clear_mask] = image_data[band_idx, clear_mask]

            file_name = 'clear_' + images[i].split('/')[-1]
            temp_images.append(os.path.join(data_dir, file_name))

            with rasterio.open(os.path.join(data_dir, file_name), 'w', **profile) as dst:
                dst.write(masked_image)
            
        if not temp_images:
            continue

        temp_images.append(images[0])

        output_file = os.path.join(data_dir, "merge_"+collection_name.split('-')[0]+"_"+scene+"_"+band+".tif")  

        datasets = []
        for file in temp_images:
            try:
                dataset = rasterio.open(file)
                datasets.append(dataset)
            except rasterio.errors.RasterioIOError as e:
                continue
        
        if not datasets:
            continue

        extents = get_dataset_extents(datasets)

        try:
            merge_tifs(tif_files=temp_images, output_path=output_file, band=band, path_row=scene, extent=extents)
        except Exception as e:
            continue

        merge_files.append(output_file)

        for dataset in datasets:
            dataset.close()

        for f in temp_images:
            try:
                os.remove(f)
            except:
                pass


    return dict(merge_files=merge_files)

def merge_scene_provenance_cloud(sorted_data, cloud_sorted_data, scenes, collection_name, band, data_dir):

    merge_files = []
    provenance_merge_files = []
    cloud_merge_files = []
    
    for scene in scenes:

        images =  [item['file'] for item in sorted_data if item.get("scene") == scene]
        cloud_images = [item['file'] for item in cloud_sorted_data if item.get("scene") == scene]
        
        temp_images = []
        provenance_temp_images = []
        temp_cloud_images = []

        for i in tqdm.tqdm(range(0, len(images)), desc="Processing..."):

            try:
                with rasterio.open(images[i]) as src:
                    image_data = src.read()  
                    profile = src.profile  
                    height, width = src.shape  
            except rasterio.errors.RasterioIOError as e:
                continue

            try:
                with rasterio.open(cloud_images[i]) as mask_src:
                    cloud_mask = mask_src.read(1) 
                    cloud_mask = mask_src.read(
                        1,  
                        out_shape=(height, width), 
                        resampling=Resampling.nearest  
                    )
            except rasterio.errors.RasterioIOError as e:
                continue
            
            cloud_dict = get_all_cloud_configs()
            clear_mask = np.isin(cloud_mask, cloud_dict[collection_name]['non_cloud_values'])

            if 'nodata' not in profile or profile['nodata'] is None:
                profile['nodata'] = 0  

            masked_image = np.full_like(image_data, profile['nodata'])
            masked_image[:, clear_mask] = image_data[:, clear_mask]  

            masked_cloud_image = np.full_like(cloud_mask, profile['nodata'])
            masked_cloud_image[clear_mask] = cloud_mask[clear_mask] 

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
            provenance_temp_images.append(os.path.join(data_dir, provenance_file_name))

            cloud_file_name = 'clear_cloud-band_' + images[i].split('/')[-1]
            temp_cloud_images.append(os.path.join(data_dir, cloud_file_name))

            with rasterio.open(os.path.join(data_dir, file_name), 'w', **profile) as dst:
                dst.write(masked_image)
            
            with rasterio.open(os.path.join(data_dir, provenance_file_name), 'w', **profile) as dst:
                dst.write(provenance)

            with rasterio.open(os.path.join(data_dir, cloud_file_name), 'w', **profile) as dst:
                dst.write(masked_cloud_image, 1) 
                
            if i==0:
                first_provenance = os.path.join(data_dir, provenance_file_name)
                first_cloud = os.path.join(data_dir, cloud_file_name)

        if not temp_images:
            continue

        temp_images.append(images[0])
        provenance_temp_images.append(first_provenance)
        temp_cloud_images.append(first_cloud)

        output_file = os.path.join(data_dir, "merge_"+collection_name.split('-')[0]+"_"+scene+"_"+band+".tif")  
        provenance_output_file = os.path.join(data_dir, "provenance_merge_"+collection_name.split('-')[0]+"_"+scene+".tif") 
        cloud_output_file = os.path.join(data_dir, "cloud_merge_"+collection_name.split('-')[0]+"_"+scene+".tif") 

        datasets = []
        for file in temp_images:
            try:
                dataset = rasterio.open(file)
                datasets.append(dataset)
            except rasterio.errors.RasterioIOError as e:
                continue
        
        if not datasets:
            continue

        extents = get_dataset_extents(datasets)

        try:
            merge_tifs(tif_files=temp_images, output_path=output_file, band=band, path_row=scene, extent=extents)
        except Exception as e:
            continue

        try:
            merge_tifs(tif_files=provenance_temp_images, output_path=provenance_output_file, band=band, path_row=scene, extent=extents)
        except Exception as e:
            continue

        try:
            merge_tifs(tif_files=temp_cloud_images, output_path=cloud_output_file, band=band, path_row=scene, extent=extents)
        except Exception as e:
            continue
        
        merge_files.append(output_file)
        provenance_merge_files.append(provenance_output_file)
        cloud_merge_files.append(cloud_output_file)

        for dataset in datasets:
            dataset.close()

        for f in temp_images:
            try:
                os.remove(f)
            except:
                pass

        for f in provenance_temp_images:
            try:
                os.remove(f)
            except:
                pass

        for f in temp_cloud_images:
            try:
                os.remove(f)
            except:
                pass

    return dict(merge_files=merge_files, provenance_merge_files=provenance_merge_files, cloud_merge_files=cloud_merge_files)
