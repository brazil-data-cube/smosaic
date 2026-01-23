import os
import tqdm
import shutil
import datetime
import rasterio

import numpy as np

from rasterio.warp import Resampling

from smosaic.smosaic_count_pixels import count_pixels
from smosaic.smosaic_get_dataset_extents import get_dataset_extents
from smosaic.smosaic_merge_tifs import merge_tifs
from smosaic.smosaic_utils import clean_dir, get_all_cloud_configs


def merge_scene(sorted_data, cloud_sorted_data, scenes, collection_name, band, data_dir, projection_output, start_date=None, end_date=None):

    temp_images = []
    non_clear_band = []

    images =  [item['file'] for item in sorted_data]
    cloud_images = [item['file'] for item in cloud_sorted_data]
    

    for i in tqdm.tqdm(range(0, len(images)), desc=f"Processing {band}..."):

        image_filename = images[i].split('/')[-1].split('.')[0]

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

        if i in [0,1,2]:
            non_clear_band_file_name = f"band_non_clear_{image_filename}.tif"
            profile['driver'] = 'GTiff'
            with rasterio.open(os.path.join(data_dir, non_clear_band_file_name), 'w', **profile) as dst:
                dst.write(image_data)
            non_clear_band.append(os.path.join(data_dir, non_clear_band_file_name))
    
        cloud_dict = get_all_cloud_configs()
        clear_mask = np.isin(cloud_mask, cloud_dict[collection_name]['non_cloud_values'])

        if 'nodata' not in profile or profile['nodata'] is None:
            profile['nodata'] = 0   # arrumar caso ndvi

        masked_image = np.full_like(image_data, profile['nodata'])
        masked_image[:, clear_mask] = image_data[:, clear_mask]  

        file_name = 'clear_' + image_filename + '.tif'
        temp_images.append(os.path.join(data_dir, file_name))

        profile['driver'] = 'GTiff'
        with rasterio.open(os.path.join(data_dir, file_name), 'w', **profile) as dst:
            dst.write(masked_image)

    temp_images = temp_images + non_clear_band
    nodata_value = profile['nodata']
    
    with rasterio.open(temp_images[0]) as src:
        composite = src.read()
        profile = src.profile

    if np.isnan(nodata_value):
        is_valid = ~np.isnan(composite)
    else:
        is_valid = (composite != nodata_value)
    
    for i in range(1, len(temp_images)):

        with rasterio.open(temp_images[i]) as src:
            img = src.read()
        
        composite_nodata = ~is_valid
        
        if np.isnan(nodata_value):
            img_valid = ~np.isnan(img)
        else:
            img_valid = (img != nodata_value)
        
        fill_mask = composite_nodata & img_valid
        
        composite[fill_mask] = img[fill_mask]
        
    collection_prefix = collection_name.split('-')[0]
    start_date_str = str(start_date).replace("-", "")
    end_date_str = str(end_date).replace("-", "")

    base_name = f"merge_{collection_prefix}_{band}_{start_date_str}_{end_date_str}"

    output_file = os.path.join(data_dir, f"{base_name}.tif")

    with rasterio.open(os.path.join(data_dir, output_file), 'w', **profile) as dst:
        dst.write(composite)
    
    date_list = [
        filename.split("T")[0][-8:] 
        for filename in temp_images 
    ]

    clean_dir(data_dir=data_dir,date_list=date_list)

    return dict(merge_files=[output_file])


def merge_scene_provenance_cloud(sorted_data, cloud_sorted_data, scenes, collection_name, band, data_dir, projection_output, start_date=None, end_date=None):

    temp_images = []
    provenance_temp_images = []
    temp_cloud_images = []

    non_clear_band = []
    non_clear_prov = []
    non_clear_clou = []

    images =  [item['file'] for item in sorted_data]
    cloud_images = [item['file'] for item in cloud_sorted_data ]

    with rasterio.open(images[0]) as src:
        image_data = src.read()  
        profile = src.profile

    for i in tqdm.tqdm(range(0, len(images)), desc=f"Processing {band}..."):

        image_filename = images[i].split('/')[-1].split('.')[0]
        cloud_filename = cloud_images[i].split('/')[-1].split('.')[0]

        with rasterio.open(images[i]) as src:
            image_data = src.read()  
            profile = src.profile  
            height, width = src.shape  

        with rasterio.open(cloud_images[i]) as mask_src:
            cloud_mask = mask_src.read(1) 
            cloud_profile = src.profile  
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

        parts = os.path.basename(image_filename).split('_')
        if (collection_name=='S2_L2A-1'):
            date = parts[2].split('T')[0]
        elif (collection_name=='S2_L1C_BUNDLE-1'):
            date = parts[1].split('T')[0]

        datatime_image = datetime.datetime.strptime(date, "%Y%m%d")
        day_of_year = datatime_image.timetuple().tm_yday

        provenance = np.full_like(masked_image, profile['nodata'])

        if i in [0,1,2]:
            non_clear_band_file_name = f"band_non_clear_{image_filename}.tif"
            profile['driver'] = 'GTiff'
            with rasterio.open(os.path.join(data_dir, non_clear_band_file_name), 'w', **profile) as dst:
                dst.write(image_data)
            shutil.copy2(cloud_images[i], os.path.join(data_dir))
            non_clear_provenance = np.full_like(image_data, day_of_year)
            non_clear_provenance_file_name = f"provenance_non_clear_{image_filename}.tif"
            with rasterio.open(os.path.join(data_dir, non_clear_provenance_file_name), 'w', **profile) as dst:
                dst.write(non_clear_provenance)
            non_clear_band.append(os.path.join(data_dir, non_clear_band_file_name))
            non_clear_clou.append(os.path.join(data_dir, cloud_images[i]))
            non_clear_prov.append(os.path.join(data_dir, non_clear_provenance_file_name))

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

    temp_images = temp_images + non_clear_band
    provenance_temp_images = provenance_temp_images + non_clear_prov
    temp_cloud_images = temp_cloud_images + non_clear_clou

    nodata_value = profile['nodata']
    
    with rasterio.open(temp_images[0]) as src:
        composite = src.read()
        profile = src.profile
        target_height, target_width = composite.shape[1], composite.shape[2]
    
    with rasterio.open(provenance_temp_images[0]) as src:
        prov_composite = src.read()
        profile = src.profile

    with rasterio.open(temp_cloud_images[0]) as src:
        cloud_composite = src.read(
            out_shape=(src.count, target_height, target_width),
            resampling=Resampling.nearest
        )
        profile = src.profile

    if np.isnan(nodata_value):
        is_valid = ~np.isnan(composite)
    else:
        is_valid = (composite != nodata_value)
    
    for i in range(1, len(temp_images)):

        with rasterio.open(temp_images[i]) as src:
            img = src.read()
            target_height, target_width = img.shape[1], img.shape[2]
        
        with rasterio.open(provenance_temp_images[i]) as src:
            prov_img = src.read()
        
        with rasterio.open(temp_cloud_images[i]) as src:
            cloud_img = src.read()
            cloud_img = src.read(
                out_shape=(src.count, target_height, target_width),
                resampling=Resampling.nearest
            )

        composite_nodata = ~is_valid
        
        if np.isnan(nodata_value):
            img_valid = ~np.isnan(img)
        else:
            img_valid = (img != nodata_value)
        
        fill_mask = composite_nodata & img_valid
        
        composite[fill_mask] = img[fill_mask]
        prov_composite[fill_mask] = prov_img[fill_mask]
        cloud_composite[fill_mask] = cloud_img[fill_mask]
        
    collection_prefix = collection_name.split('-')[0]
    start_date_str = str(start_date).replace("-", "")
    end_date_str = str(end_date).replace("-", "")

    base_name = f"merge_{collection_prefix}_{band}_{start_date_str}_{end_date_str}"
    provenance_base_name = f"provenance_merge_{collection_prefix}_{start_date_str}_{end_date_str}"
    cloud_base_name = f"cloud_merge_{collection_prefix}_{start_date_str}_{end_date_str}"

    output_file = os.path.join(data_dir, f"{base_name}.tif")
    provenance_output_file = os.path.join(data_dir, f"{provenance_base_name}.tif")
    cloud_output_file = os.path.join(data_dir, f"{cloud_base_name}.tif")

    with rasterio.open(os.path.join(data_dir, output_file), 'w', **profile) as dst:
        dst.write(composite)

    with rasterio.open(os.path.join(data_dir, provenance_output_file), 'w', **profile) as dst:
        dst.write(prov_composite)

    with rasterio.open(os.path.join(data_dir, cloud_output_file), 'w', **profile) as dst:
        dst.write(cloud_composite)
    
    date_list = [
        filename.split("T")[0][-8:] 
        for filename in temp_images 
    ]

    clean_dir(data_dir=data_dir,date_list=date_list)

    return dict(merge_files=[output_file], provenance_merge_files=[provenance_output_file], cloud_merge_files=[cloud_output_file])