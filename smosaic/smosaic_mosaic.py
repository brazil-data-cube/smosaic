import os
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
from smosaic.smosaic_generate_cog import generate_cog
from smosaic.smosaic_get_dataset_extents import get_dataset_extents
from smosaic.smosaic_merge_scene import merge_scene, merge_scene_provenance_cloud
from smosaic.smosaic_merge_tifs import merge_tifs
from smosaic.smosaic_utils import add_days_to_date, add_months_to_date, clean_dir, days_between_dates, get_all_cloud_configs


def mosaic(name, data_dir, stac_url, collection, output_dir, start_year, start_month, start_day, bands, mosaic_method, reference_date=None, duration_days=None, end_year=None, end_month=None, end_day=None, duration_months=None, geom=None, grid=None, grid_id=None, bbox=None):

    stac = pystac_client.Client.open(stac_url)

    if collection not in ['S2_L2A-1']: #'S2-16D-2'
        return print(f"{collection['collection']} collection not yet supported.")
    
    #geometry
    if (geom):
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
        end_date = add_days_to_date(start_date,duration_days)
    
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
        
    dict_collection=collection_query(
        collection=collection,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        bbox=bbox,
        bands=bands
    )   
    
    collection_name = dict_collection['collection']

    collection_get_data(stac, dict_collection, data_dir=data_dir)
        
    num_processes = multiprocessing.cpu_count()
    print(f"--- Starting parallel processing with {num_processes} processes. ---\n")
    
    args_for_processes = [
        (period, mosaic_method, data_dir, collection_name, bands, bbox, output_dir, duration_days, duration_months, name, geom, reference_date) for period in periods
    ]

    with multiprocessing.Pool(processes=num_processes) as pool:
        results = pool.starmap(process_period, args_for_processes)

    clean_dir(data_dir)


def process_period(period, mosaic_method, data_dir, collection_name, bands, bbox, output_dir, duration_days, duration_months, name, geom, reference_date):
    
    start_date = period['start']
    end_date = period['end']

    process_id = os.getpid()
    
    print(f"[Process {process_id}] Starting to process period: {start_date} to {end_date}\n")
    
    coll_data_dir = os.path.join(data_dir+'/'+collection_name)

    for i in range(0, len(bands)):

        if (i==0):
            cloud_dict = get_all_cloud_configs()
            bands_cloud = [bands[i]] + [cloud_dict[collection_name]['cloud_band']]
            cloud_list = []   
        else:
            bands_cloud = [bands[i]] 
        
        band_list = []             
        sorted_data = []

        scenes = filter_scenes(collection_name, data_dir, bbox)

        cloud = cloud_dict[collection_name]['cloud_band']

        for path in scenes:
            filtered_files = [
                f for f in os.listdir(os.path.join(coll_data_dir, path, cloud))
                if (datetime.datetime.strptime(f.split("_")[2].split('T')[0], "%Y%m%d") >= datetime.datetime.strptime(start_date, "%Y-%m-%d") and datetime.datetime.strptime(f.split("_")[2].split('T')[0], "%Y%m%d") <= datetime.datetime.strptime(end_date, "%Y-%m-%d"))
            ]
            for file in filtered_files:
                date = datetime.datetime.strptime(file.split("_")[2].split('T')[0], "%Y%m%d")
                if (reference_date):
                    distance_days = days_between_dates(reference_date, file.split("_")[2].split('T')[0])
                    pixel_count = count_pixels(os.path.join(coll_data_dir, path, cloud_dict[collection_name]['cloud_band'], file), cloud_dict[collection_name]['non_cloud_values'][0]) #por região não total
                    cloud_list.append(dict(band=cloud, date=date.strftime("%Y%m%d"), distance_days=distance_days, clean_percentage=float(pixel_count['count']/pixel_count['total']), scene=path, file=''))
                    band_list.append(dict(band=bands[i], date=date.strftime("%Y%m%d"), distance_days=distance_days, clean_percentage=float(pixel_count['count']/pixel_count['total']), scene=path, file=''))

                else:
                    pixel_count = count_pixels(os.path.join(coll_data_dir, path, cloud_dict[collection_name]['cloud_band'], file), cloud_dict[collection_name]['non_cloud_values'][0]) #por região não total
                    cloud_list.append(dict(band=cloud, date=date.strftime("%Y%m%d"), clean_percentage=float(pixel_count['count']/pixel_count['total']), scene=path, file=''))
                    band_list.append(dict(band=bands[i], date=date.strftime("%Y%m%d"), clean_percentage=float(pixel_count['count']/pixel_count['total']), scene=path, file=''))

        #print(f"Building {bands[i]} mosaic using {len(scenes)} scenes from the {collection_name}.")

        files_list = []

        for path in scenes:
            for band in bands_cloud:
                filtered_files = [
                    f for f in os.listdir(os.path.join(coll_data_dir, path, band))
                    if (datetime.datetime.strptime(f.split("_")[2].split('T')[0], "%Y%m%d") >= datetime.datetime.strptime(start_date, "%Y-%m-%d") and datetime.datetime.strptime(f.split("_")[2].split('T')[0], "%Y%m%d") <= datetime.datetime.strptime(end_date, "%Y-%m-%d"))
                ]
                for file in filtered_files:
                    files_list.append(dict(file=os.path.join(coll_data_dir, path, band, file)))

        band_lookup, cloud_lookup = {}, {}
        for f in files_list:
            path = f['file']
            parts = os.path.basename(path).split('_')
            date, scene = parts[2].split('T')[0], parts[5].lstrip('T')
            band_lookup[(parts[1], date, scene)] = path
            cloud_lookup[(date, scene)] = path

        for item in band_list:
            item['file'] = band_lookup.get((item['band'], item['date'], item['scene']), '')

        for item in cloud_list:
            item['file'] = cloud_lookup.get((item['date'], item['scene']), '')

        if (mosaic_method=='lcf'):

            sorted_data = sorted(band_list, key=lambda x: x['clean_percentage'], reverse=True)
            
            cloud_sorted_data = sorted(cloud_list, key=lambda x: x['clean_percentage'], reverse=True)

            if (i==0):
                ordered_lists = merge_scene_provenance_cloud(sorted_data, cloud_sorted_data, scenes, collection_name, bands[i], data_dir)
            else:
                ordered_lists = merge_scene(sorted_data, cloud_sorted_data, scenes, collection_name, bands[i], data_dir)

        if (mosaic_method=='crono'):

            sorted_data = sorted(band_list, key=lambda x: x['date'])

            cloud_sorted_data = sorted(cloud_list, key=lambda x: x['date'])

            if (i==0):
                ordered_lists = merge_scene_provenance_cloud(sorted_data, cloud_sorted_data, scenes, collection_name, bands[i], data_dir)
            else:
                ordered_lists = merge_scene(sorted_data, cloud_sorted_data, scenes, collection_name, bands[i], data_dir)

        if (mosaic_method=='ctd'):

            sorted_data = sorted(band_list, key=lambda x: x['distance_days'])
            
            cloud_sorted_data = sorted(cloud_list, key=lambda x: x['distance_days'])

            if (i==0):
                ordered_lists = merge_scene_provenance_cloud(sorted_data, cloud_sorted_data, scenes, collection_name, bands[i], data_dir)
            else:
                ordered_lists = merge_scene(sorted_data, cloud_sorted_data, scenes, collection_name, bands[i], data_dir)
        
        band = bands[i]

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        if (duration_months):
            file_name = "mosaic-"+collection_name.split("-")[0].lower()+"-"+name.lower()+"-"+str(duration_months)+"m"+"-"+bands[i]+"-"+str(start_date).replace("-", "")+'_'+str(end_date).replace("-", "")
        elif (duration_days):
            file_name = "mosaic-"+collection_name.split("-")[0].lower()+"-"+name.lower()+"-"+str(duration_days)+"d"+"-"+bands[i]+"-"+str(start_date).replace("-", "")+'_'+str(end_date).replace("-", "")

        output_file = os.path.join(output_dir, "raw-"+file_name+".tif")

        if (i==0):
            provenance_output_file = os.path.join(output_dir, "provenance_raw-"+file_name+".tif")  
            cloud_data_output_file = os.path.join(output_dir, "cloud_data_raw-"+file_name+".tif") 
        
        datasets = [rasterio.open(file) for file in  ordered_lists['merge_files']]        
        
        extents = get_dataset_extents(datasets)
        
        merge_tifs(tif_files= ordered_lists['merge_files'], output_path=output_file, band=band, path_row=name, extent=extents)
        if (i==0):
            merge_tifs(tif_files=ordered_lists['provenance_merge_files'], output_path=provenance_output_file, band=band, path_row=name, extent=extents)
            merge_tifs(tif_files=ordered_lists['cloud_merge_files'], output_path=cloud_data_output_file, band=band, path_row=name, extent=extents)

        clip_raster(input_raster_path=output_file, output_folder=output_dir, clip_geometry=geom, output_filename=file_name+".tif")
        if (i==0):
            clip_raster(input_raster_path=provenance_output_file, output_folder=output_dir, clip_geometry=geom, output_filename=file_name.replace("-"+bands[i]+"-", "-PROVENANCE-")+".tif")
            clip_raster(input_raster_path=cloud_data_output_file, output_folder=output_dir, clip_geometry=geom, output_filename=file_name.replace("-"+bands[i]+"-", "-"+cloud_dict[collection_name]['cloud_band']+"-")+".tif")
        
        generate_cog(input_folder=output_dir, input_filename=file_name, compress='LZW')
        if (i==0):
            generate_cog(input_folder=output_dir, input_filename=file_name.replace("-"+bands[i]+"-", "-PROVENANCE-"), compress='LZW')
            generate_cog(input_folder=output_dir, input_filename=file_name.replace("-"+bands[i]+"-", "-"+cloud_dict[collection_name]['cloud_band']+"-"), compress='LZW')