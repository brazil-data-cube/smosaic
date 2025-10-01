import os
import tqdm
import json
import osgeo
import pyproj
import shapely
import dateutil
import rasterio
import requests
import datetime
import importlib
import numpy as np
import pystac_client

from osgeo import gdal
from shapely.ops import transform as shapely_transform
from rasterio.merge import merge as rasterio_merge
from rasterio.mask import mask as rasterio_mask
from rasterio.warp import calculate_default_transform, reproject, Resampling

cloud_dict = {
    'S2-16D-2':{
        'cloud_band': 'SCL',
        'non_cloud_values': [4,5,6],
        'cloud_values': [0,1,2,3,7,8,9,10,11],
        'no_data_value': 0
    },
    'S2_L2A-1':{
        'cloud_band': 'SCL',
        'non_cloud_values': [4,5,6],
        'cloud_values': [0,1,2,3,7,8,9,10,11],
        'no_data_value': 0
    },
    'AMZ1-WFI-L4-SR-1':{
        'cloud_band': 'CMASK',
        'non_cloud_values': [127],
        'cloud_values': [255, 0],
        'no_data_value': 0
    }
}

coverage_proj = pyproj.CRS.from_wkt('''
    PROJCS["unknown",
        GEOGCS["unknown",
            DATUM["Unknown based on GRS80 ellipsoid",
                SPHEROID["GRS 1980",6378137,298.257222101,
                    AUTHORITY["EPSG","7019"]]],
            PRIMEM["Greenwich",0,
                AUTHORITY["EPSG","8901"]],
            UNIT["degree",0.0174532925199433,
                AUTHORITY["EPSG","9122"]]],
        PROJECTION["Albers_Conic_Equal_Area"],
        PARAMETER["latitude_of_center",-12],
        PARAMETER["longitude_of_center",-54],
        PARAMETER["standard_parallel_1",-2],
        PARAMETER["standard_parallel_2",-22],
        PARAMETER["false_easting",5000000],
        PARAMETER["false_northing",10000000],
        UNIT["metre",1,
        AUTHORITY["EPSG","9001"]],
        AXIS["Easting",EAST],
        AXIS["Northing",NORTH]]''')

def open_geojson(file_path):
    
    geojson_data = json.load(open(file_path, 'r', encoding='utf-8'))

    return shapely.geometry.shape(geojson_data["features"][0]["geometry"]) if geojson_data["type"] == "FeatureCollection" else shapely.geometry.shape(geojson_data)

def load_jsons(cut_grid):
    if (cut_grid == "grids"):
        grid_json_path = importlib.resources.files("smosaic.config") / "grids.json"
        return json.loads(grid_json_path.read_text(encoding="utf-8"))
    if (cut_grid == "states"):
        states_json_path = importlib.resources.files("smosaic.config") / "br_states.json"
        return json.loads(states_json_path.read_text(encoding="utf-8"))

def collection_query(collection, start_date, end_date, tile=None, bbox=None, freq=None, bands=None):
    """An object that contains the information associated with a collection 
    that can be downloaded or acessed.

    Args:
        collection : String containing a collection id.

        start_date String containing the start date of the associated collection. Following YYYY-MM-DD structure.

        end_date : String containing the start date of the associated collection. Following YYYY-MM-DD structure.

        freq : Optional, string containing the frequency of images of the associated collection. Following (days)D structure. 

        bands : Optional, string containing the list bands id.
    """

    return dict(
        collection = collection,
        bands = bands,
        start_date = start_date,
        tile = tile,
        bbox = bbox,
        end_date = end_date
    )

def download_stream(file_path: str, response, chunk_size=1024*64, progress=True, offset=0, total_size=None):
    """Download request stream data to disk.

    Args:
        file_path - Absolute file path to save
        response - HTTP Response object
    """
    parent = os.path.dirname(file_path)

    if parent:
        os.makedirs(parent, exist_ok=True)

    if not total_size:
        total_size = int(response.headers.get('Content-Length', 0))

    file_name = os.path.basename(file_path)

    progress_bar = tqdm.tqdm(
        desc=file_name[:30]+'... ',
        total=total_size,
        unit="B",
        unit_scale=True,
        #disable=not progress,
        initial=offset,
        disable=True
    )

    mode = 'a+b' if offset else 'wb'

    with response:
        with open(file_path, mode) as stream:
            for chunk in response.iter_content(chunk_size):
                stream.write(chunk)
                progress_bar.update(chunk_size)

    file_size = os.stat(file_path).st_size

    if file_size != total_size:
        os.remove(file_path)
        raise IOError(f'Download file is corrupt. Expected {total_size} bytes, got {file_size}')

def collection_get_data(stac, datacube, data_dir):
    
    collection = datacube['collection']
    bbox = datacube['bbox']
    start_date = datacube['start_date']
    end_date = datacube['end_date']
    bands = datacube['bands'] + [cloud_dict[collection]['cloud_band']]

    if (datacube['bbox']):
        item_search = stac.search(
            collections=[collection],
            datetime=start_date+"T00:00:00Z/"+end_date+"T23:59:00Z",
            bbox=bbox
        )
        
    tiles = []
    for item in item_search.items():
        if (collection=="AMZ1-WFI-L4-SR-1"):
            tile = item.id.split("_")[4]+'_'+item.id.split("_")[5]
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
                
    for tile in tiles:
        #print(data_dir+"/"+collection+"/"+tile)      
        if not os.path.exists(data_dir+"/"+collection+"/"+tile):
            os.makedirs(data_dir+"/"+collection+"/"+tile)
        for band in bands:
            if not os.path.exists(data_dir+"/"+collection+"/"+tile+"/"+band):
                os.makedirs(data_dir+"/"+collection+"/"+tile+"/"+band)

    geom_map = []
    download = False

    for item in tqdm.tqdm(desc='Downloading... ', unit=" itens", total=item_search.matched(), iterable=item_search.items()):
        for band in bands:
            if (collection=="AMZ1-WFI-L4-SR-1"):
                tile = item.id.split("_")[4]+'_'+item.id.split("_")[5]
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

def download_stream(file_path: str, response, chunk_size=1024*64, progress=True, offset=0, total_size=None):
    """Download request stream data to disk.

    Args:
        file_path - Absolute file path to save
        response - HTTP Response object
    """
    parent = os.path.dirname(file_path)

    if parent:
        os.makedirs(parent, exist_ok=True)

    if not total_size:
        total_size = int(response.headers.get('Content-Length', 0))

    file_name = os.path.basename(file_path)

    progress_bar = tqdm.tqdm(
        desc=file_name[:30]+'... ',
        total=total_size,
        unit="B",
        unit_scale=True,
        #disable=not progress,
        initial=offset,
        disable=True
    )

    mode = 'a+b' if offset else 'wb'

    with response:
        with open(file_path, mode) as stream:
            for chunk in response.iter_content(chunk_size):
                stream.write(chunk)
                progress_bar.update(chunk_size)

    file_size = os.stat(file_path).st_size

    if file_size != total_size:
        os.remove(file_path)
        raise IOError(f'Download file is corrupt. Expected {total_size} bytes, got {file_size}')

def clip_raster(input_raster_path, output_folder, clip_geometry, output_filename=None):
    """
    Clip a raster using a Shapely geometry and save the result to another folder.
    
    Parameters:
    - input_raster_path: Path to the input raster file
    - output_folder: Folder where the clipped raster will be saved
    - clip_geometry: Shapely geometry object used for clipping
    - output_filename: Optional output filename (defaults to input filename with '_clipped' suffix)
    
    Returns:
    - Path to the saved clipped raster
    """
    
    os.makedirs(output_folder, exist_ok=True)
    
    if output_filename is None:
        base_name = os.path.basename(input_raster_path)
        name, ext = os.path.splitext(base_name)
        output_filename = f"{name}_clipped{ext}"
    
    output_path = os.path.join(output_folder, output_filename)
    
    with rasterio.open(input_raster_path) as src:
        out_image, out_transform = rasterio_mask (
            src, 
            [shapely.geometry.mapping(clip_geometry)],  
            crop=True,
            all_touched=True
        )
        
        out_meta = src.meta.copy()
        
        out_meta.update({
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })
        
        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(out_image)
            
    os.remove(input_raster_path)
    return output_path

def count_pixels_with_value(raster_path, target_value):
    """
    Counts the number of pixels in a raster that match a specific value.
    
    Args:
        raster_path (str): Path to the raster file
        target_value (int/float): The pixel value to count
        
    Returns:
        int: Count of pixels with the target value
    """
    
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        
        count = (data == target_value).sum()
        
        return dict(total=data.size, count=count)

def get_dataset_extents(datasets):
    extents = []
    for ds in datasets:

        left, bottom, right, top = ds.bounds
        
        extent = shapely.geometry.box(left, bottom, right, top)
        
        data_proj = ds.crs
        proj_converter = pyproj.Transformer.from_crs(data_proj, pyproj.CRS.from_epsg(4326), always_xy=True).transform
        reproj_bbox = shapely_transform(proj_converter, extent)
        
        extents.append(reproj_bbox)
        
    return shapely.geometry.MultiPolygon(extents).bounds

def add_months_to_date(start_date, months_to_add):
    """
    Add months to a date and return the last day of the FINAL month.
    (Fixes the issue where adding N months would overshoot)
    
    Args:
        start_date (datetime/str): Starting date
        months_to_add (int): Months to add (positive or negative)
    
    Returns:
        datetime: Last day of the target month
    """
    if isinstance(start_date, str):
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    
    target_date = start_date + dateutil.relativedelta.relativedelta(months=months_to_add)

    return target_date + dateutil.relativedelta.relativedelta(day=31)

def merge_tifs(tif_files, output_path, band, path_row=None, extent=None):
    """
    Merge a list of TIFF files into one mosaic, reprojecting to EPSG:4326.
    
    Parameters:
    -----------
    tif_files : list
        List of paths to input TIFF files
    output_path : str
        Path to save the merged output TIFF
    extent : tuple (optional)
        Bounding box for output in format (minx, miny, maxx, maxy) in EPSG:4326.
        If None, will use the combined extent of all input files.
    """
    
    reprojected_files = []
    bounds = []
    
    for tif in tif_files:
        with rasterio.open(tif) as src:
            
            left, bottom, right, top = src.bounds
            src_extent = shapely.geometry.box(left, bottom, right, top)
            
            proj_converter = pyproj.Transformer.from_crs(
                src.crs, 
                'EPSG:4326', 
                always_xy=True
            ).transform
            
            reproj_bbox = shapely_transform(proj_converter, src_extent)
            bounds.append(reproj_bbox.bounds)
            
            dst_crs = 'EPSG:4326'
            
            dst_transform, width, height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds
            )
            
            reproj_data = np.zeros((src.count, height, width), dtype=src.dtypes[0])
            
            reproject(
                source=rasterio.band(src, range(1, src.count + 1)),
                destination=reproj_data,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs=dst_crs,
                resampling=Resampling.nearest,
                nodata=0
            )
            
            temp_path = f'temp_{os.path.basename(tif)}'
            reprojected_files.append(temp_path)

            cloud_bands = [item['cloud_band'] for item in cloud_dict.values()]

            if band in cloud_bands:
                nodata = 0 
            else:
                nodata = 0 

            with rasterio.open(
                temp_path,
                'w',
                driver='GTiff',
                height=height,
                width=width,
                count=src.count,
                dtype=reproj_data.dtype,
                crs=dst_crs,
                transform=dst_transform,
                nodata= nodata
            ) as dst:
                dst.write(reproj_data)
    
    if extent is None:
        minx = min(b[0] for b in bounds)
        miny = min(b[1] for b in bounds)
        maxx = max(b[2] for b in bounds)
        maxy = max(b[3] for b in bounds)
        extent = (minx, miny, maxx, maxy)
    else:
        minx, miny, maxx, maxy = extent
    
    src_files_to_mosaic = []
    for f in reprojected_files:
        src = rasterio.open(f)
        src_files_to_mosaic.append(src)
    
    mosaic, out_trans = rasterio_merge(src_files_to_mosaic, bounds=extent)
    
    out_meta = src.meta.copy()
    out_meta.update({
        "driver": "GTiff",
        "height": mosaic.shape[1],
        "width": mosaic.shape[2],
        "transform": out_trans,
        "crs": 'EPSG:4326'
    })
    
    with rasterio.open(output_path, "w", **out_meta) as dest:
        dest.write(mosaic)

    if(path_row):
        print(f"Successfully merged {len(src_files_to_mosaic)} files for {path_row} scene.")
    else:
        print(f"Successfully merged {len(src_files_to_mosaic)} files.")
    
    for src in src_files_to_mosaic:
        src.close()
    
    for f in reprojected_files:
        try:
            os.remove(f)
        except:
            pass
    return output_path

def merge_scene(sorted_data, cloud_sorted_data, scenes, collection_name, band, data_dir):

    merge_files = []
    for scene in scenes:

        images =  [item['file'] for item in sorted_data if item.get("scene") == scene]
        cloud_images = [item['file'] for item in cloud_sorted_data if item.get("scene") == scene]
        temp_images = []

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
            clear_mask = np.isin(cloud_mask, cloud_dict[collection_name]['non_cloud_values'])

            if 'nodata' not in profile or profile['nodata'] is None:
                profile['nodata'] = 0  

            masked_image = np.full_like(image_data, profile['nodata'])

            for band_idx in range(image_data.shape[0]):
                masked_image[band_idx, clear_mask] = image_data[band_idx, clear_mask]

            file_name = 'clear_' + images[i].split('/')[-1]
            temp_images.append(os.path.join(data_dir, file_name))

            with rasterio.open(os.path.join(data_dir, file_name), 'w', **profile) as dst:
                dst.write(masked_image)

        temp_images.append(images[0])

        output_file = os.path.join(data_dir, "merge_"+collection_name.split('-')[0]+"_"+scene+"_"+band+".tif")  

        datasets = [rasterio.open(file) for file in temp_images]  
        
        extents = get_dataset_extents(datasets)

        merge_tifs(tif_files=temp_images, output_path=output_file, band=band, path_row=scene, extent=extents)

        merge_files.append(output_file)

        for f in temp_images:
            try:
                os.remove(f)
            except:
                pass


    return merge_files

def geometry_collides_with_bbox(geometry,input_bbox):
    """
    Check if a Shapely geometry collides with a bounding box.
    
    Args:
        geometry: A Shapely geometry object (Polygon, LineString, Point, etc.)
        bbox: A tuple in (minx, miny, maxx, maxy) format
        
    Returns:
        bool: True if the geometry intersects with the bbox, False otherwise
    """

    bbox_polygon = shapely.geometry.box(*input_bbox)
    
    return geometry.intersects(bbox_polygon)

def filter_scenes(collection, data_dir, bbox):
    """
    Return scenes from data_dir where the geometry collides with the bounding box.
    
    Args:
        collection: A string with BDC collection id
        data_dir: A string with directory
        bbox: A tuple in (minx, miny, maxx, maxy) format
        
    Returns:
        list: Scenes filtered by when geometry collides with the bounding box.
    """

    collection_metadata = json.load(open(os.path.join(data_dir, collection, str(collection+".json")), 'r', encoding='utf-8'))
    
    list_dir = [item for item in os.listdir(os.path.join(data_dir, collection))
            if os.path.isdir(os.path.join(data_dir, collection, item))]
    
    filtered_list = []
    
    for scene in list_dir:
        item = [item for item in collection_metadata['geoms'] if item["tile"] == scene]
        if (geometry_collides_with_bbox(shapely.geometry.shape(item[0]['geometry']), bbox)):
            filtered_list.append(item[0]['tile'])   
          
    return filtered_list

def clean_dir(data_dir):
    files_to_delete = [
        os.path.join(data_dir, f) 
        for f in os.listdir(data_dir) 
        if f.startswith("merge_")
    ]
    
    for f in files_to_delete:
        try:
            os.remove(f)
        except:
            pass

def generate_cog(input_folder: str, input_filename: str, compress: str = 'LZW') -> str:
    """Generate COG file."""
    input_file = os.path.join(input_folder, f'{input_filename}.tif')
    output_file = os.path.join(input_folder, f'{input_filename}_COG.tif')

    gdal.Translate(
        output_file,
        input_file,
        options=gdal.TranslateOptions(
            format='COG',
            creationOptions=[
                f'COMPRESS={compress}',
                'BIGTIFF=IF_SAFER'
            ],
            outputType=gdal.GDT_Int16
        )
    )

    try:
        os.remove(input_file)
    except:
        pass

    print(f"Raster saved to: {output_file}")
    
    return output_file

def mosaic(name, data_dir, stac_url, collection, output_dir, start_year, start_month, start_day, duration_months, bands, mosaic_method, geom=None, grid=None, grid_id=None):

    stac = pystac_client.Client.open(stac_url)

    if collection not in ['S2_L2A-1', 'S2-16D-2']:
        return print(f"{collection['collection']} collection not yet supported.")
    
    # grid
    if (grid != None and grid_id!= None):
        if (grid == "br_states"):
            br_states = load_jsons("states")
            
            state_code = grid_id.upper()
            
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
                        if tile['properties']['tile'] == grid_id:
                            selected_tile = tile
            geom = selected_tile['properties']['geometry']
            bbox = shapely.geometry.shape(geom).bounds
            geom = shapely.geometry.shape(geom["features"][0]["geometry"]) if geom["type"] == "FeatureCollection" else shapely.geometry.shape(geom)

    # geometry
    else:
        bbox = geom.bounds

    start_date = datetime.datetime.strptime(str(start_year)+'-'+str(start_month)+'-'+str(start_day), "%Y-%m-%d").strftime("%Y-%m-%d")
    end_date = str(add_months_to_date(start_date, duration_months-1).strftime('%Y-%m-%d'))

    dict_collection=collection_query(
        collection=collection,
        start_date=start_date,
        end_date=end_date,
        bbox=bbox,
        bands=bands
    )   
    
    collection_name = dict_collection['collection']

    collection_get_data(stac, dict_collection, data_dir=data_dir)
    
    if (mosaic_method=='lcf'):

        coll_data_dir = os.path.join(data_dir+'/'+collection_name)

        for i in range(len(bands)):
            if (i==0):
                bands_cloud = [bands[i]] + [cloud_dict[collection_name]['cloud_band']]
                cloud_list = []   
            else:
                bands_cloud = [bands[i]] 
            
            band_list = []             
            sorted_data = []

            scenes = filter_scenes(collection_name, data_dir, bbox)

            cloud = cloud_dict[collection]['cloud_band']

            if (i==0):
                print(f"Building {cloud} mosaic using {len(scenes)} scenes from the {collection}.")
                
            for path in scenes:
                for file in os.listdir(os.path.join(coll_data_dir, path, cloud)):
                    pixel_count = count_pixels_with_value(os.path.join(coll_data_dir, path, cloud_dict[collection]['cloud_band'], file), cloud_dict[collection]['non_cloud_values'][0]) #por região não total
                    if (collection=="AMZ1-WFI-L4-SR-1"):
                        date = file.split("_")[3]
                    else:
                        date = file.split("_")[2].split('T')[0]
                    cloud_list.append(dict(band=cloud, date=date, clean_percentage=float(pixel_count['count']/pixel_count['total']), scene=path, file=''))
                    band_list.append(dict(band=bands[i], date=date, clean_percentage=float(pixel_count['count']/pixel_count['total']), scene=path, file=''))

            print(f"Building {bands[i]} mosaic using {len(scenes)} scenes from the {collection_name}.")
            
            bands_links = []
            cloud_links = []
            for path in scenes:
                for band in bands_cloud:
                    for file in os.listdir(os.path.join(coll_data_dir, path, band)):
                        if (collection_name=="AMZ1-WFI-L4-SR-1"):
                            date = file.split("_")[3]
                        else:
                            date = file.split("_")[2].split('T')[0]
                        if(band == cloud_dict[collection_name]['cloud_band']):
                            for item in cloud_list:
                                if item['date'] == date:
                                    item['file'] = os.path.join(coll_data_dir, path, band, file)
                                    if (i==0):
                                        cloud_links.append(dict(band=band, date=date, clean_percentage=item['clean_percentage'], scene=path, file=os.path.join(coll_data_dir, path, band, file)))
                        else:
                            for item in band_list:
                                if item['date'] == date:
                                    bands_links.append(dict(band=band, date=date, clean_percentage=item['clean_percentage'], scene=path, file=os.path.join(coll_data_dir, path, band, file)))

            sorted_data = sorted(bands_links, key=lambda x: x['clean_percentage'], reverse=True)

            if (i==0):
                cloud_sorted_data = sorted(cloud_links, key=lambda x: x['clean_percentage'], reverse=True)
            
            lcf_list = merge_scene(sorted_data, cloud_sorted_data, scenes, collection_name, bands[i], data_dir)

            band = bands[i]

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            output_file = os.path.join(output_dir, "raw-mosaic-"+collection_name.split("-")[0].lower()+"-"+band.lower()+"-"+name+"-"+str(duration_months)+"m.tif")  
            
            datasets = [rasterio.open(file) for file in lcf_list]        
            
            extents = get_dataset_extents(datasets)
            
            merge_tifs(tif_files=lcf_list, output_path=output_file, band=band, path_row=name, extent=extents)
            
            clip_raster(input_raster_path=output_file, output_folder=output_dir, clip_geometry=geom,output_filename="mosaic-"+collection_name.split("-")[0].lower()+"-"+band.lower()+"-"+name+"-"+str(duration_months)+"m.tif")
            
            generate_cog(input_folder=output_dir, input_filename="mosaic-"+collection_name.split("-")[0].lower()+"-"+bands[i].lower()+"-"+name+"-"+str(duration_months)+"m", compress='LZW')

            clean_dir(data_dir)