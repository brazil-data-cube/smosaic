import os
import tqdm
import json
import requests

from smosaic.smosaic_download_stream import download_stream
from smosaic.smosaic_utils import get_all_cloud_configs


def collection_get_data(stac, datacube, data_dir):
    
    collection = datacube['collection']
    bbox = datacube['bbox']
    start_date = datacube['start_date']
    end_date = datacube['end_date']
    cloud_dict = get_all_cloud_configs()
    bands = datacube['bands'] + [cloud_dict[collection]['cloud_band']]

    if (datacube['bbox']):
        item_search = stac.search(
            collections=[collection],
            datetime=start_date+"T00:00:00Z/"+end_date+"T23:59:00Z",
            bbox=bbox
        )

    tiles = []
    for item in item_search.items():
        if (collection=="S2_L2A-1"):
            tile = item.id.split("_")[5][1:]
            if tile not in tiles:
                tiles.append(tile)
        if (collection=="S2-16D-2"):
            tile = item.id.split("_")[2]
            if tile not in tiles:
                tiles.append(tile)
                
    for tile in tiles:      
        if not os.path.exists(data_dir+"/"+collection+"/"+tile):
            os.makedirs(data_dir+"/"+collection+"/"+tile)
        for band in bands:
            if not os.path.exists(data_dir+"/"+collection+"/"+tile+"/"+band):
                os.makedirs(data_dir+"/"+collection+"/"+tile+"/"+band)

    geom_map = []
    download = False

    for item in tqdm.tqdm(desc='Downloading... ', unit=" itens", total=item_search.matched(), iterable=item_search.items()):
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

    print(f"Successfully download {item_search.matched()} files to {os.path.join(collection)}")