import os
import tqdm
import shutil
import datetime
import rasterio

import numpy as np

from rasterio.warp import Resampling

from smosaic.smosaic_utils import clean_dir, get_all_cloud_configs


def merge_scene(sorted_data, cloud_sorted_data, scenes, collection_name, band, data_dir, start_date=None, end_date=None):

    temp_images = []

    merge_files = []

    images =  [item['file'] for item in sorted_data]
    cloud_images = [item['file'] for item in cloud_sorted_data]

    with rasterio.open(images[0]) as src:
        image_data = src.read()  
        profile = src.profile

    non_clear_band = []

    for i in tqdm.tqdm(range(0, len(images)), desc=f"Processing {band}..."):

        image_filename = images[i].split('/')[-1].split('.')[0]

        with rasterio.open(images[i]) as src:
            image_data = src.read()  
            profile = src.profile  
            height, width = src.shape  

        with rasterio.open(cloud_images[i]) as mask_src:
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

        file_name = 'clear_' + image_filename + '.tif'
        temp_images.append(os.path.join(data_dir, file_name))

        profile['driver'] = 'GTiff'

        with rasterio.open(os.path.join(data_dir, file_name), 'w', **profile) as dst:
            dst.write(masked_image)

    for scene in scenes:
        
        for i in [0,1, 2]:

            images =  [item['file'] for item in sorted_data if item.get("scene") == scene]

            image_filename = images[i].split('/')[-1].split('.')[0]

            with rasterio.open(images[i]) as src:
                image_data = src.read()  
                height, width = src.shape 
            
            non_clear_band_file_name = f"band_non_clear_{image_filename}.tif"
            profile['driver'] = 'GTiff'
            with rasterio.open(os.path.join(data_dir, non_clear_band_file_name), 'w', **profile) as dst:
                dst.write(image_data)

            non_clear_band.append(os.path.join(data_dir, non_clear_band_file_name))

    temp_images = temp_images + non_clear_band

    for scene in scenes:
        filtered_temp_images = list(filter(lambda x: scene in x, temp_images))
        
        with rasterio.open(filtered_temp_images[0]) as src:
            composite = src.read()
            profile = src.profile

        nodata_value = profile['nodata']
        
        if nodata_value is None or not isinstance(nodata_value, (int, float, np.number)):
            is_valid = np.ones_like(composite, dtype=bool)
        else:
            if np.isnan(nodata_value):
                is_valid = ~np.isnan(composite)
            else:
                is_valid = (composite != nodata_value)

        for i in range(1, len(filtered_temp_images)):

            with rasterio.open(filtered_temp_images[i]) as src:
                img = src.read()

            if nodata_value is None or not isinstance(nodata_value, (int, float, np.number)):
                img_valid = np.ones_like(img, dtype=bool)
            else:
                if np.isnan(nodata_value):
                    img_valid = ~np.isnan(img)
                else:
                    img_valid = (img != nodata_value)
            
            fill_mask = (~is_valid) & img_valid
                    
            composite[fill_mask] = img[fill_mask]
            
            is_valid = is_valid | fill_mask
            
        collection_prefix = collection_name.split('-')[0]
        start_date_str = str(start_date).replace("-", "")
        end_date_str = str(end_date).replace("-", "")

        base_name = f"merge_{collection_prefix}_{band}_{scene}_{start_date_str}_{end_date_str}"

        output_file = os.path.join(data_dir, f"{base_name}.tif")
        with rasterio.open(output_file, 'w', **profile) as dst:
            dst.write(composite)

        merge_files.append(output_file)

    date_list = [
        filename.split("T")[0][-8:] 
        for filename in temp_images 
    ]

    clean_dir(data_dir=data_dir,date_list=date_list)

    return dict(merge_files=merge_files)

def merge_scene_provenance_cloud(sorted_data, cloud_sorted_data, scenes, collection_name, band, data_dir, start_date=None, end_date=None):

    temp_images = []
    provenance_temp_images = []
    temp_cloud_images = []

    merge_files = []
    provenance_merge_files = []
    cloud_merge_files = []

    images =  [item['file'] for item in sorted_data]
    cloud_images = [item['file'] for item in cloud_sorted_data]

    with rasterio.open(images[0]) as src:
        image_data = src.read()  
        profile = src.profile

    non_clear_band = []
    non_clear_prov = []
    non_clear_clou = []

    for i in tqdm.tqdm(range(0, len(images)), desc=f"Processing {band}..."):

        image_filename = images[i].split('/')[-1].split('.')[0]
        cloud_filename = cloud_images[i].split('/')[-1].split('.')[0]

        with rasterio.open(images[i]) as src:
            image_data = src.read()  
            profile = src.profile  
            height, width = src.shape  

        with rasterio.open(cloud_images[i]) as mask_src:
            cloud_profile = mask_src.profile  
            cloud_mask = mask_src.read(
                1,  
                out_shape=(height, width), 
                resampling=Resampling.nearest  
            )

        cloud_dict = get_all_cloud_configs()
        clear_mask = np.isin(cloud_mask, cloud_dict[collection_name]['non_cloud_values'])

        if 'nodata' not in profile or profile['nodata'] is None:
            profile['nodata'] = 0 
        
        cloud_profile['nodata'] = cloud_dict[collection_name]['no_data_value']

        masked_image = np.full_like(image_data, profile['nodata'])
        masked_image[:, clear_mask] = image_data[:, clear_mask]  

        masked_cloud_image = np.full_like(cloud_mask, cloud_profile['nodata'])
        masked_cloud_image[clear_mask] = cloud_mask[clear_mask]

        image_filename = images[i].split('/')[-1].split('.')[0]
        parts = image_filename.split('_')
        for part in parts:
            if part[0:4].isdigit() and len(part) >= 9 and part[8] == 'T':
                date = part.split('T')[0]
                break

        datatime_image = datetime.datetime.strptime(date, "%Y%m%d")
        day_of_year = datatime_image.timetuple().tm_yday

        provenance = np.full_like(masked_image, profile['nodata'])

        valid_mask = masked_image != profile['nodata']
        provenance[valid_mask] = day_of_year

        file_name = 'clear_' + image_filename + '.tif'
        temp_images.append(os.path.join(data_dir, file_name))

        provenance_file_name = 'provenance_' + image_filename + '.tif'
        provenance_temp_images.append(os.path.join(data_dir, provenance_file_name))

        cloud_item_file_name = 'clear_cloud-band_' + cloud_filename + '.tif'
        temp_cloud_images.append(os.path.join(data_dir, cloud_item_file_name))

        profile['driver'] = 'GTiff'

        with rasterio.open(os.path.join(data_dir, file_name), 'w', **profile) as dst:
            dst.write(masked_image)
        
        with rasterio.open(os.path.join(data_dir, provenance_file_name), 'w', **profile) as dst:
            dst.write(provenance)

        profile['nodata'] = cloud_dict[collection_name]['no_data_value']

        with rasterio.open(os.path.join(data_dir, cloud_item_file_name), 'w', **profile) as dst:
            dst.write(masked_cloud_image, 1)

    for scene in scenes:
        
        for i in [0,1, 2]:

            images =  [item['file'] for item in sorted_data if item.get("scene") == scene]
            cloud_images = [item['file'] for item in cloud_sorted_data if item.get("scene") == scene]

            image_filename = images[i].split('/')[-1].split('.')[0]
            cloud_filename = cloud_images[i].split('/')[-1].split('.')[0]

            with rasterio.open(images[i]) as src:
                image_data = src.read()  
                height, width = src.shape 

            with rasterio.open(cloud_images[i]) as mask_src:
                cloud_mask = mask_src.read(
                    1,  
                    out_shape=(height, width), 
                    resampling=Resampling.nearest  
                )

            parts = image_filename.split('_')
            for part in parts:
                if part[0:4].isdigit() and len(part) >= 9 and part[8] == 'T':
                    date = part.split('T')[0]
                    break

            datatime_image = datetime.datetime.strptime(date, "%Y%m%d")
            day_of_year = datatime_image.timetuple().tm_yday
            
            non_clear_band_file_name = f"band_non_clear_{image_filename}.tif"
            profile['driver'] = 'GTiff'
            with rasterio.open(os.path.join(data_dir, non_clear_band_file_name), 'w', **profile) as dst:
                dst.write(image_data)

            non_clear_cloud_file_name = f"cloud_non_clear_{image_filename}.tif"
            with rasterio.open(os.path.join(data_dir, non_clear_cloud_file_name), 'w', **profile) as dst:
                dst.write(cloud_mask, 1)

            non_clear_provenance = np.full_like(image_data, day_of_year)
            non_clear_provenance_file_name = f"provenance_non_clear_{image_filename}.tif"
            with rasterio.open(os.path.join(data_dir, non_clear_provenance_file_name), 'w', **profile) as dst:
                dst.write(non_clear_provenance)

            non_clear_band.append(os.path.join(data_dir, non_clear_band_file_name))
            non_clear_clou.append(os.path.join(data_dir, non_clear_cloud_file_name))
            non_clear_prov.append(os.path.join(data_dir, non_clear_provenance_file_name))

    temp_images = temp_images + non_clear_band
    provenance_temp_images = provenance_temp_images + non_clear_prov
    temp_cloud_images = temp_cloud_images + non_clear_clou

    for scene in scenes:
        filtered_temp_images = list(filter(lambda x: scene in x, temp_images))
        filtered_provenance_temp_images = list(filter(lambda x: scene in x, provenance_temp_images))
        filtered_temp_cloud_images = list(filter(lambda x: scene in x, temp_cloud_images))
        
        with rasterio.open(filtered_temp_images[0]) as src:
            composite = src.read()
            profile = src.profile

        with rasterio.open(filtered_provenance_temp_images[0]) as src:
            prov_composite = src.read()

        with rasterio.open(filtered_temp_cloud_images[0]) as src:
            cloud_composite = src.read()

        nodata_value = profile['nodata']
        
        if nodata_value is None or not isinstance(nodata_value, (int, float, np.number)):
            is_valid = np.ones_like(composite, dtype=bool)
        else:
            if np.isnan(nodata_value):
                is_valid = ~np.isnan(composite)
            else:
                is_valid = (composite != nodata_value)

        for i in range(1, len(filtered_temp_images)):

            with rasterio.open(filtered_temp_images[i]) as src:
                img = src.read()
                profile = src.profile

            with rasterio.open(filtered_provenance_temp_images[i]) as src:
                prov_img = src.read()

            with rasterio.open(filtered_temp_cloud_images[i]) as src:
                cloud_img = src.read()

            if nodata_value is None or not isinstance(nodata_value, (int, float, np.number)):
                img_valid = np.ones_like(img, dtype=bool)
            else:
                if np.isnan(nodata_value):
                    img_valid = ~np.isnan(img)
                else:
                    img_valid = (img != nodata_value)
            
            fill_mask = (~is_valid) & img_valid
                    
            composite[fill_mask] = img[fill_mask]
            prov_composite[fill_mask] = prov_img[fill_mask]
            cloud_composite[fill_mask] = cloud_img[fill_mask]
            
            is_valid = is_valid | fill_mask
            
        collection_prefix = collection_name.split('-')[0]
        start_date_str = str(start_date).replace("-", "")
        end_date_str = str(end_date).replace("-", "")

        base_name = f"merge_{collection_prefix}_{band}_{scene}_{start_date_str}_{end_date_str}"
        provenance_base_name = f"provenance_merge_{collection_prefix}_{scene}_{start_date_str}_{end_date_str}"
        cloud_base_name = f"cloud_merge_{collection_prefix}_{scene}_{start_date_str}_{end_date_str}"

        output_file = os.path.join(data_dir, f"{base_name}.tif")
        provenance_output_file = os.path.join(data_dir, f"{provenance_base_name}.tif")
        cloud_output_file = os.path.join(data_dir, f"{cloud_base_name}.tif")

        with rasterio.open(output_file, 'w', **profile) as dst:
            dst.write(composite)

        with rasterio.open(provenance_output_file, 'w', **profile) as dst:
            dst.write(prov_composite)

        with rasterio.open(cloud_output_file, 'w', **profile) as dst:
            dst.write(cloud_composite)

        merge_files.append(output_file)
        provenance_merge_files.append(provenance_output_file)
        cloud_merge_files.append(cloud_output_file)

    date_list = [
        filename.split("T")[0][-8:] 
        for filename in temp_images 
    ]

    clean_dir(data_dir=data_dir,date_list=date_list)

    return dict(merge_files=merge_files, provenance_merge_files=provenance_merge_files, cloud_merge_files=cloud_merge_files)