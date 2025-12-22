import os
    
from smosaic.smosaic_utils import find_grid_by_name


def filter_scenes(collection, data_dir, bbox):

    #if (collection in ['S2_L2A-1','S2_L1C_BUNDLE-1']):
    #    grid_data = find_grid_by_name("MGRS")
    
    list_dir = [item for item in os.listdir(os.path.join(data_dir, collection))
            if os.path.isdir(os.path.join(data_dir, collection, item))]
    
    filtered_list = []
    
    for scene in list_dir:
        #item = [item for item in grid_data["features"] if item["properties"]["name"] == scene]
        #if (geometry_collides_with_bbox(shapely.geometry.shape(item[0]["geometry"]), bbox)):
        filtered_list.append(scene)

    return filtered_list
