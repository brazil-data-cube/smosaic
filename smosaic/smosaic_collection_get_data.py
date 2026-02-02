import os
import re
import tqdm
import json
import shutil
import requests

from smosaic.smosaic_download_stream import download_stream
from smosaic.smosaic_utils import get_all_cloud_configs


def collection_get_data(stac, datacube, data_dir):
    """
    Fetch and download data from a STAC collection based on specified parameters.
    
    Args:
        stac (str): Brazil Data Cube STAC API endpoint URL (e.g., "https://data.inpe.br/bdc/stac/v1").
        datacube (dict): Dictionary containing collection query parameters with the following keys:
            collection (str): Identifier of the STAC collection to query.
            start_date (str): Start date for temporal filtering in 'YYYY-MM-DD' format.
            end_date (str): End date for temporal filtering in 'YYYY-MM-DD' format.
            bbox (list/tuple): Bounding box coordinates [minx, miny, maxx, maxy] for spatial filtering.
            bands (list, optional): List of band identifiers to include in the download.
        data_dir (str): Directory path where the downloaded data will be stored.
    """
    collection = datacube['collection']
    bbox = datacube['bbox']
    start_date = datacube['start_date']
    end_date = datacube['end_date']
    cloud_dict = get_all_cloud_configs()
    if(collection=="S2_L1C_BUNDLE-1"):
        bands = "asset"
    else:
        bands = datacube['bands'] + [cloud_dict[collection]['cloud_band']]

    if (datacube['bbox']):
        item_search = stac.search(
            collections=[collection],
            datetime=start_date+"T00:00:00Z/"+end_date+"T23:59:00Z",
            bbox=bbox
        )

    tiles = []
    for item in item_search.items():
        if (collection=="S2_L1C_BUNDLE-1"):
            tile = item.id.split("_")[5][1:]
            if tile not in tiles:
                tiles.append(tile)
        if (collection=="S2_L2A-1"):
            tile = item.id.split("_")[5][1:]
            if tile not in tiles:
                tiles.append(tile)
        if (collection=="S2-16D-2"):
            tile = item.id.split("_")[2]
            if tile not in tiles:
                tiles.append(tile)

    if(collection=="S2_L1C_BUNDLE-1"):
        bands = datacube['bands'] + [cloud_dict[collection]['cloud_band']]

    for tile in tiles:      
        if not os.path.exists(data_dir+"/"+collection+"/"+tile):
            os.makedirs(data_dir+"/"+collection+"/"+tile)
        for band in bands:
            if not os.path.exists(data_dir+"/"+collection+"/"+tile+"/"+band):
                os.makedirs(data_dir+"/"+collection+"/"+tile+"/"+band)

    geom_map = []
    download = False

    for item in tqdm.tqdm(desc='Downloading... ', unit=" itens", total=item_search.matched(), iterable=item_search.items()):
        if (collection=="S2_L1C_BUNDLE-1"):
            tile = item.id.split("_")[5][1:]
            band = 'asset'
            response = requests.get(item.assets[band].href, stream=True)
            download = True
            download_stream(os.path.join(data_dir+"/"+collection+"/"+tile, os.path.basename(item.assets[band].href)), response, total_size=item.to_dict()['assets'][band]["bdc:size"])
        else:
            for band in bands:
                if (collection=="S2_L2A-1"):
                    tile = item.id.split("_")[5][1:]
                if (collection=="S2-16D-2"):
                    tile = item.id.split("_")[2]
                response = requests.get(item.assets[band].href, stream=True)
                if not any(tile_dict["tile"] == tile for tile_dict in geom_map):
                    geom_map.append(dict(tile=tile, geometry=item.geometry))
                if(os.path.exists(os.path.join(data_dir+"/"+collection+"/"+tile+"/"+band, os.path.basename(item.assets[band].href)))):
                    download = False
                else:
                    download = True
                    download_stream(os.path.join(data_dir+"/"+collection+"/"+tile+"/"+band, os.path.basename(item.assets[band].href)), response, total_size=item.to_dict()['assets'][band]["bdc:size"])
        
    if(download):
        file_name = collection+".json"
        with open(os.path.join(data_dir+"/"+collection+"/"+file_name), 'w') as json_file:
            json.dump(dict(collection=collection, geoms=geom_map), json_file, indent=4)

    if (collection=="S2_L1C_BUNDLE-1"):
        for tile in tiles:
                tile_path = os.path.join(data_dir+"/"+collection+"/"+tile)
                pattern_zip = r'\.zip$'
                files_zip = [
                    os.path.join(tile_path, f) for f in os.listdir(tile_path)
                    if re.search(pattern_zip, f)
                ]

                for zip_file in files_zip:
                    shutil.unpack_archive(zip_file, tile_path)
                    os.remove(zip_file)

                item_imgs_path = None
                for item in os.listdir(tile_path):
                    if item.startswith("S2"):
                        item_path = os.path.join(data_dir+"/"+collection+"/"+tile+"/"+item)
                        granule_path = os.path.join(data_dir+"/"+collection+"/"+tile+"/"+item+"/"+"GRANULE")
                        for item_imgs in os.listdir(granule_path):
                            if item_imgs.startswith("L1"):
                                item_imgs_path = os.path.join(data_dir+"/"+collection+"/"+tile+"/"+item+"/"+"GRANULE"+"/"+item_imgs+"/"+"IMG_DATA")


                        if item_imgs_path and os.path.exists(item_imgs_path):
                            for band in bands:
                                band_path = os.path.join(data_dir, collection, tile, band)
                                pattern_band = r'_{}'.format(band)
                                for file in os.listdir(item_imgs_path):
                                    if re.search(pattern_band, file):
                                        file_path = os.path.join(item_imgs_path, file)
                                        shutil.copy(file_path, band_path)

            #for folder in os.listdir(tile_path):
                #folder_path = os.path.join(tile_path, folder)
                #if folder.startswith("S2") and os.path.isdir(folder_path):
                    #shutil.rmtree(folder_path)

    print(f"Successfully download {item_search.matched()} files to {os.path.join(collection)}")