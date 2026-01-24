import os
import re
import json
import shapely
import rasterio
import datetime
import dateutil
import pystac_client
import multiprocessing

from smosaic.smosaic_clip_raster import clip_raster
from smosaic.smosaic_collection_get_data import collection_get_data
from smosaic.smosaic_collection_query import collection_query
from smosaic.smosaic_count_pixels import count_pixels
from smosaic.smosaic_filter_scenes import filter_scenes
from smosaic.smosaic_fix_baseline_number import fix_baseline_number
from smosaic.smosaic_generate_cog import generate_cog
from smosaic.smosaic_get_dataset_extents import get_dataset_extents
from smosaic.smosaic_grid_crop import clip_from_grid
from smosaic.smosaic_merge_scene import merge_scene, merge_scene_provenance_cloud
from smosaic.smosaic_merge_tifs import merge_tifs
from smosaic.smosaic_reproject_tif import reproject_tif
from smosaic.smosaic_spectral_indices import calculate_spectral_indices
from smosaic.smosaic_utils import add_days_to_date, add_months_to_date, clean_dir, create_composition_json, days_between_dates, get_all_cloud_configs, load_jsons


def mosaic(name, data_dir, stac_url, collection, output_dir, start_year, start_month, start_day, mosaic_method, grid_crop=False, bands=None, reference_date=None, duration_days=None, end_year=None, end_month=None, end_day=None, duration_months=None, geom=None, grid=None, tile_id=None, bbox=None, profile=None, projection_output=4326):
    
    clean_dir(data_dir)

    stac = pystac_client.Client.open(stac_url)

    if collection not in ['S2_L2A-1','S2_L1C_BUNDLE-1']: #'S2-16D-2'
        return print(f"{collection['collection']} collection not yet supported.")
    
    # grid
    if (grid != None and tile_id!= None):
        if (grid == "br_states"):
            br_states = load_jsons("states")
            
            state_code = tile_id.upper()
            
            for feature in br_states['features']:
                if feature['id'] == state_code:
                    geom = feature['geometry']
                    bbox = shapely.geometry.shape(geom).bounds
                    geom = shapely.geometry.shape(geom["features"][0]["geometry"]) if geom["type"] == "FeatureCollection" else shapely.geometry.shape(geom)
        else:
            bdc_grids_data = load_jsons("grids")
            selected_tile = ''
            for g in bdc_grids_data['grids']:
                if (g['name'] == grid):
                    for tile in g['features']:
                        if tile['properties']['tile'] == tile_id:
                            selected_tile = tile
            geom = selected_tile['geometry']
            bbox = shapely.geometry.shape(geom).bounds
            geom = shapely.geometry.shape(geom["features"][0]["geometry"]) if geom["type"] == "FeatureCollection" else shapely.geometry.shape(geom)

    #geometry
    elif (geom):
        bbox = geom.bounds
    
    #bbox
    else:
        tuple_bbox = tuple(map(float, bbox.split(',')))
        geom = shapely.geometry.box(*tuple_bbox)
        bbox = geom.bounds

    start_date = datetime.datetime.strptime(str(start_year)+'-'+str(start_month)+'-'+str(start_day), "%Y-%m-%d")

    end_date = None
    if all(v is not None for v in [end_year, end_month, end_day]):
        end_date = datetime.datetime.strptime(str(end_year)+'-'+str(end_month)+'-'+str(end_day), "%Y-%m-%d")
    elif duration_months is not None:
        end_date = add_months_to_date(start_date,duration_months-1)
    elif duration_days is not None and not any([end_year, end_month, end_day, duration_months]):
        end_date = add_days_to_date(start_date,duration_days-1)
    
    if end_date is None:
        return print("Not provided with a valid time interval.")

    periods = []
    current_start_date = start_date

    if duration_days:
        while current_start_date <= end_date:
            current_end_date = add_days_to_date(current_start_date,duration_days-1)

            if current_end_date > end_date:
                current_end_date = end_date
            if current_start_date != current_end_date:
                periods.append({
                    'start': current_start_date.strftime("%Y-%m-%d"),
                    'end': current_end_date.strftime("%Y-%m-%d")
                })
            current_start_date += datetime.timedelta(days=duration_days)
    elif duration_months:
        while current_start_date <= end_date:
            current_end_date = current_start_date + dateutil.relativedelta.relativedelta(months=duration_months) - dateutil.relativedelta.relativedelta(days=1)

            if current_end_date > end_date:
                current_end_date = end_date
            if current_start_date != current_end_date:
                periods.append({
                    'start': current_start_date.strftime("%Y-%m-%d"),
                    'end': current_end_date.strftime("%Y-%m-%d")
                })
            current_start_date = current_start_date + dateutil.relativedelta.relativedelta(months=duration_months)
    else:
        periods.append({
            'start': start_date.strftime("%Y-%m-%d"),
            'end': end_date.strftime("%Y-%m-%d")
        })
        
    if profile=="crop_condition":
        bands = ["B02","B04","B08"]
        spectral_indices = ["NDVI","EVI","EVI2", "SAVI"]
    elif profile=="urban_analysis":
        bands = ["B02","B03","B04","B08","B11"]
        spectral_indices = ["NDBI","NDVI"]
    else:
        spectral_indices = []

    dict_collection=collection_query(
        collection=collection,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        bbox=bbox,
        bands=bands
    )   
    
    collection_name = dict_collection['collection']

    if not os.path.exists(data_dir+"/"+collection):
        collection_get_data(stac, dict_collection, data_dir=data_dir)

    num_processes = multiprocessing.cpu_count()

    args_for_processes = [
        (period, mosaic_method, data_dir, collection_name, bands, bbox, output_dir, 
         duration_days, duration_months, name, geom, reference_date, projection_output) 
        for period in periods
    ]

    print(f"--- Starting parallel processing with {num_processes} processes. ---\n")

    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.starmap(process_period, args_for_processes)

    return 0 

    if(len(spectral_indices)):
        calculate_spectral_indices(input_folder=output_dir,spectral_indices=spectral_indices)

    if (grid_crop):
        clip_from_grid(input_folder=output_dir, grid=grid, tile_id=tile_id)

    scenes = filter_scenes(collection_name, data_dir, geom)

    create_composition_json(output_dir=output_dir, collection=collection, input_scenes=scenes, ignored_scenes=[], used_scenes=[])

    clean_dir(data_dir)


def process_period(period, mosaic_method, data_dir, collection_name, bands, bbox, output_dir, duration_days, duration_months, name, geom, reference_date, projection_output):

    start_date = period['start']
    end_date = period['end']

    process_id = os.getpid()

    print(f"[Process {process_id}] Starting to process period: {start_date} to {end_date}\n")
    
    coll_data_dir = os.path.join(data_dir+'/'+collection_name)

    for i in range(0, len(bands)):

        cloud_dict = get_all_cloud_configs()

        cloud_list = []   
        band_list = []             
        sorted_data = []

        bands_cloud = [bands[i]] + [cloud_dict[collection_name]['cloud_band']]
        
        scenes = filter_scenes(collection_name, data_dir, geom)

        cloud = cloud_dict[collection_name]['cloud_band']

        for path in scenes:

            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")

            filtered_files = [
                f for f in os.listdir(os.path.join(coll_data_dir, path, cloud))
                if (date_match := re.search(r'\d{8}', f)) and
                (date_str := date_match.group()) and
                len(date_str) == 8 and
                date_str.isdigit() and
                (file_date := datetime.datetime.strptime(date_str, "%Y%m%d")) and
                start_dt <= file_date <= end_dt
            ]

            for file in filtered_files:
                date_match = re.search(r'\d{8}', file)
                date_str = date_match.group()
                date = datetime.datetime.strptime(date_str, "%Y%m%d")
                if (reference_date):
                    distance_days = days_between_dates(reference_date, file.split("_")[2].split('T')[0])
                    pixel_count = count_pixels(os.path.join(coll_data_dir, path, cloud_dict[collection_name]['cloud_band'], file), cloud_dict[collection_name]['non_cloud_values'], geom) 
                    cloud_list.append(dict(band=cloud, date=date.strftime("%Y%m%d"), distance_days=distance_days, clean_percentage=float(pixel_count['count']/pixel_count['total']), scene=path, file='')) 
                    band_list.append(dict(band=bands[i], date=date.strftime("%Y%m%d"), distance_days=distance_days, clean_percentage=float(pixel_count['count']/pixel_count['total']), scene=path, file=''))
                else:
                    pixel_count = count_pixels(os.path.join(coll_data_dir, path, cloud_dict[collection_name]['cloud_band'], file), cloud_dict[collection_name]['non_cloud_values'], geom)
                    cloud_list.append(dict(band=cloud, date=date.strftime("%Y%m%d"), clean_percentage=float(pixel_count['count']/pixel_count['total']), scene=path, file=''))
                    band_list.append(dict(band=bands[i], date=date.strftime("%Y%m%d"), clean_percentage=float(pixel_count['count']/pixel_count['total']), scene=path, file=''))

        files_list = []

        for path in scenes:
            for band in bands_cloud:
                start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")

                filtered_files = [
                    f for f in os.listdir(os.path.join(coll_data_dir, path, band))
                    if (date_match := re.search(r'\d{8}', f)) and
                    (date_str := date_match.group()) and
                    len(date_str) == 8 and
                    date_str.isdigit() and
                    (file_date := datetime.datetime.strptime(date_str, "%Y%m%d")) and
                    start_dt <= file_date <= end_dt
                ]

                for file in filtered_files:
                    files_list.append(dict(file=os.path.join(coll_data_dir, path, band, file)))        

        band_lookup, cloud_lookup = {}, {}
        for f in files_list:
            path = f['file']
            parts = os.path.basename(path).split('_')
            if (len(parts)>4):
                date, scene, band = parts[2].split('T')[0], parts[5].lstrip('T'), parts[1]
            else:
                date, scene, band = parts[1].split('T')[0], parts[0].lstrip('T'), parts[2].split(".")[0]
            cloud_lookup[(date, scene)] = path
            band_lookup[(band, date, scene)] = path


        for item in band_list:
            item['file'] = band_lookup.get((item['band'], item['date'], item['scene']), '')

        for item in cloud_list:
            item['file'] = cloud_lookup.get((item['date'], item['scene']), '')

        if (mosaic_method=='lcf'):

            sorted_data = sorted(band_list, key=lambda x: x['clean_percentage'], reverse=True)

            cloud_sorted_data = sorted(cloud_list, key=lambda x: x['clean_percentage'], reverse=True)
            
        if (mosaic_method=='crono'):

            sorted_data = sorted(band_list, key=lambda x: x['date'])

            cloud_sorted_data = sorted(cloud_list, key=lambda x: x['date'])

        if (mosaic_method=='ctd'):

            sorted_data = sorted(band_list, key=lambda x: x['distance_days'])

            cloud_sorted_data = sorted(cloud_list, key=lambda x: x['distance_days'])

        if (i==0):
            ordered_lists = merge_scene_provenance_cloud(sorted_data, cloud_sorted_data, scenes, collection_name, bands[i], data_dir, start_date, end_date)
        else:
            ordered_lists = merge_scene(sorted_data, cloud_sorted_data, scenes, collection_name, bands[i], data_dir, start_date, end_date,)

        filename = sorted_data[0]['file'].split('/')[-1]
        if (collection_name =='S2_L2A-1'):
            baseline_number = filename.split("_N")[1][0:4]
        else:
            baseline_number = 0

        band = bands[i]

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        collection_prefix = collection_name.split("-")[0].upper()
        name_upper = name.upper()
        date_range = f"{str(start_date).replace('-', '')}_{str(end_date).replace('-', '')}"
        current_band = bands[i]

        if duration_months:
            duration_str = f"-{duration_months}M"
        elif duration_days:
            duration_str = f"-{duration_days}D"
        else:
            duration_str = ""

        file_name = f"{collection_prefix}-{name_upper}{duration_str}-{current_band}_{date_range}"
        cloud_file_name = f"{collection_prefix}-{name_upper}{duration_str}_{cloud}_{date_range}"
        provenance_file_name = f"{collection_prefix}-{name_upper}{duration_str}-PROVENANCE_{date_range}"

        output_file = os.path.join(output_dir, f"raw-{file_name}.tif")

        if i == 0:
            cloud_data_output_file = os.path.join(output_dir, f"cloud_data_raw-{file_name}.tif")
            provenance_output_file = os.path.join(output_dir, f"provenance_raw-{file_name}.tif")
        
        datasets = [rasterio.open(file) for file in  ordered_lists['merge_files']]        
        
        extents = get_dataset_extents(datasets, projection_output)

        merge_tifs(tif_files=ordered_lists['merge_files'], output_path=output_file, band=band, path_row=name, extent=extents, projection_output=projection_output)
        if (i==0):
            merge_tifs(tif_files=ordered_lists['provenance_merge_files'], output_path=provenance_output_file, band=band, path_row=name, extent=extents, projection_output=projection_output)
            merge_tifs(tif_files=ordered_lists['cloud_merge_files'], output_path=cloud_data_output_file, band=cloud_dict[collection_name]["cloud_band"], path_row=name, extent=extents, projection_output=projection_output)


        clip_raster(input_raster_path=output_file, output_folder=output_dir, clip_geometry=geom, projection_output=projection_output, output_filename=file_name+".tif")
        if (i==0):
            clip_raster(input_raster_path=cloud_data_output_file, output_folder=output_dir, clip_geometry=geom, projection_output=projection_output, output_filename=cloud_file_name+".tif")
            clip_raster(input_raster_path=provenance_output_file, output_folder=output_dir, clip_geometry=geom, projection_output=projection_output, output_filename=provenance_file_name+".tif")
        
        fix_baseline_number(input_folder=output_dir, input_filename=file_name, baseline_number=baseline_number)

        #generate_cog(input_folder=output_dir, input_filename=file_name, compress='LZW')
        #if (i==0):
        #    generate_cog(input_folder=output_dir, input_filename=cloud_file_name, compress='LZW')
        #    generate_cog(input_folder=output_dir, input_filename=provenance_file_name, compress='LZW')
        
        reproject_tif(input_folder=output_dir, input_filename=file_name)
        if (i==0):
            reproject_tif(input_folder=output_dir, input_filename=cloud_file_name)
            reproject_tif(input_folder=output_dir, input_filename=provenance_file_name)
        
        clean_dir(data_dir=data_dir,date_interval=str("-"+str(start_date).replace("-", "")+'_'+str(end_date).replace("-", "")))