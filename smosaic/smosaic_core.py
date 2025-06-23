import requests
import os, glob
import zipfile
import pyproj
from tqdm import tqdm
from pystac_client import Client
from importlib.resources import files
import json
from json import load
import rasterio
import numpy as np
from rasterio.merge import merge
from rasterio.mask import mask
from shapely.geometry import box
from shapely.geometry import MultiPolygon
from shapely.geometry import mapping
from shapely.geometry import shape
from shapely.ops import transform
from math import cos, pi
import pyproj
from pyproj import Transformer
import shapely
import rasterio
from rasterio.merge import merge
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta

cloud_dict = {
    'S2-16D-2':{
        'cloud_band': 'SCL',
        'non_cloud_values': [4,5,6],
        'cloud_values': [0,1,2,3,7,8,9,10,11]
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

stac = Client.open("https://data.inpe.br/bdc/stac/v1")

def open_geojson(file_path):
    
    geojson_data = load(open(file_path, 'r', encoding='utf-8'))

    return shape(geojson_data["features"][0]["geometry"]) if geojson_data["type"] == "FeatureCollection" else shape(geojson_data)

def load_json():
    json_path = files("smosaic.config") / "grids.json"
    return json.loads(json_path.read_text(encoding="utf-8"))

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

    progress_bar = tqdm(
        desc=file_name[:30]+'... ',
        total=total_size,
        unit="B",
        unit_scale=True,
        disable=not progress,
        initial=offset
    )

    mode = 'a+b' if offset else 'wb'

    # May throw exception for read-only directory
    with response:
        with open(file_path, mode) as stream:
            for chunk in response.iter_content(chunk_size):
                stream.write(chunk)
                #progress_bar.update(chunk_size)

    file_size = os.stat(file_path).st_size

    if file_size != total_size:
        os.remove(file_path)
        raise IOError(f'Download file is corrupt. Expected {total_size} bytes, got {file_size}')

def unzip():
    for z in glob.glob("*.zip"):
        try:
            with zipfile.ZipFile(os.path.join(z), 'r') as zip_ref:
                #print('Unziping '+ z)
                zip_ref.extractall('unzip')
                os.remove(z)
        except:
            #print("An exception occurred")
            os.remove(z)

def collection_get_data(datacube):
    
    collection = datacube['collection']
    bbox = datacube['bbox']
    start_date = datacube['start_date']
    end_date = datacube['end_date']
    bands = datacube['bands']

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
                
    for tile in tiles:      
        if not os.path.exists(collection+"/"+tile):
            os.makedirs(collection+"/"+tile)
        for band in bands:
            if not os.path.exists(collection+"/"+tile+"/"+band):
                os.makedirs(collection+"/"+tile+"/"+band)

    for item in tqdm(desc='Downloading... ', unit=" itens", total=item_search.matched(), iterable=item_search.items()):
        for band in bands:
            tile = item.id.split("_")[4]+'_'+item.id.split("_")[5]
            response = requests.get(item.assets[band].href, stream=True)
            if(os.path.exists(os.path.join(collection+"/"+tile+"/"+band, os.path.basename(item.assets[band].href)))):
                #print(os.path.basename(item.assets[band].href)[:30]+'...', ': Already exists')
                pass
            else:
                download_stream(os.path.join(collection+"/"+tile+"/"+band, os.path.basename(item.assets[band].href)), response, total_size=item.to_dict()['assets'][band]["bdc:size"])

    print(f"Successfully download {item_search.matched()} files to {os.path.join(collection)}")

def create_multipolygon(polygons, crs=None):
    """
    Create a MultiPolygon from a list of Polygons with CRS support.
    
    Args:
        polygons: List of Shapely Polygon objects
        crs: Optional CRS (Coordinate Reference System)
        
    Returns:
        GeoDataFrame containing the MultiPolygon with CRS
    """
    # Create MultiPolygon
    multipoly = MultiPolygon(polygons)
    
    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(geometry=[multipoly], crs=crs)
    
    return gdf
    
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
    
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Determine output filename
    if output_filename is None:
        base_name = os.path.basename(input_raster_path)
        name, ext = os.path.splitext(base_name)
        output_filename = f"{name}_clipped{ext}"
    
    output_path = os.path.join(output_folder, output_filename)
    
    # Open the input raster
    with rasterio.open(input_raster_path) as src:
        # Clip the raster using the geometry
        out_image, out_transform = mask(
            src, 
            [mapping(clip_geometry)],  # Convert Shapely geometry to GeoJSON-like dict
            crop=True,
            all_touched=True
        )
        
        # Copy the metadata from the source raster
        out_meta = src.meta.copy()
        
        # Update metadata with new transform and dimensions
        out_meta.update({
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })
        
        # Write the clipped raster to disk
        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(out_image)
            
    print(f"Clipped raster saved to: {output_path}")
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
    # Open the raster file
    with rasterio.open(raster_path) as src:
        # Read all data (assuming single-band raster)
        data = src.read(1)
        
        # Count pixels with the target value
        count = (data == target_value).sum()
        
        return dict(total=data.size, count=count)
    
def get_dataset_extents(datasets):
    extents = []
    for ds in datasets:
        # Get the bounding box coordinates
        left, bottom, right, top = ds.bounds
        
        # Create a shapely Polygon representing the extent
        extent = box(left, bottom, right, top)
        
        data_proj = ds.crs
        proj_converter = Transformer.from_crs(data_proj, pyproj.CRS.from_epsg(4326), always_xy=True).transform
        reproj_bbox = transform(proj_converter, extent)
        
        # Store both the geometry and CRS
        extents.append(reproj_bbox)
        
    return MultiPolygon(extents).bounds

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
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    
    # First calculate the target month
    target_date = start_date + relativedelta(months=months_to_add)
    # Then get the last day of THAT month
    return target_date + relativedelta(day=31)
    
    return start_date + relativedelta(months=months_to_add)

def merge_tifs(tif_files, output_path, extent=None):
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
    
    # First, reproject all files to EPSG:4326 and collect their bounds
    reprojected_files = []
    bounds = []
    
    for tif in tif_files:
        with rasterio.open(tif) as src:
            # Get the bounds in source CRS
            left, bottom, right, top = src.bounds
            src_extent = box(left, bottom, right, top)
            
            # Create transformer to convert to WGS84
            proj_converter = Transformer.from_crs(
                src.crs, 
                'EPSG:4326', 
                always_xy=True
            ).transform
            
            # Transform the bounding box to WGS84
            reproj_bbox = transform(proj_converter, src_extent)
            bounds.append(reproj_bbox.bounds)
            
            # Reproject the file to WGS84
            dst_crs = 'EPSG:4326'
            
            # Calculate the transform for the reprojected image (renamed to dst_transform)
            dst_transform, width, height = calculate_default_transform(
                src.crs, dst_crs, src.width, src.height, *src.bounds
            )
            
            # Create a temporary in-memory file for the reprojected data
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
            
            # Create a temporary file path
            temp_path = f'temp_{os.path.basename(tif)}'
            reprojected_files.append(temp_path)
            
            # Write the reprojected data to a temporary file
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
                nodata=-9999
            ) as dst:
                dst.write(reproj_data)
    
    # Determine the output bounds if not provided
    if extent is None:
        minx = min(b[0] for b in bounds)
        miny = min(b[1] for b in bounds)
        maxx = max(b[2] for b in bounds)
        maxy = max(b[3] for b in bounds)
        extent = (minx, miny, maxx, maxy)
    else:
        minx, miny, maxx, maxy = extent
    
    # Open all reprojected files
    src_files_to_mosaic = []
    for f in reprojected_files:
        src = rasterio.open(f)
        src_files_to_mosaic.append(src)
    
    # Merge all files
    mosaic, out_trans = merge(src_files_to_mosaic, bounds=extent)
    
    # Write the merged file
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
    
    print(f"Successfully merged {len(src_files_to_mosaic)} files")

    # Close all files and clean up temporary files
    for src in src_files_to_mosaic:
        src.close()
    
    for f in reprojected_files:
        try:
            os.remove(f)
        except:
            pass
    
    return output_path

def mosaic(data_dir, collection, output_dir, start_year, start_month, start_day, duration_months, bands, mosaic_method, geom=None, grid=None, grid_id=None):
    
    #bdc grid
    if (grid != None and grid_id!= None):
        bdc_grids_data = load_json()
        selected_tile = ''
        for g in bdc_grids_data['grids']:
            if (g['name'] == grid):
                for tile in g['features']:
                    if tile['properties']['tile'] == grid_id:
                        selected_tile = tile
        geometry = selected_tile['properties']['geometry']
        bbox = shape(geometry).bounds

    #geometry
    else:
        bbox = geom.bounds

    start_date = datetime.strptime(str(start_year)+'-'+str(start_month)+'-'+str(start_day), "%Y-%m-%d").strftime("%Y-%m-%d")
    end_date = str(add_months_to_date(start_date, duration_months-1).strftime('%Y-%m-%d'))

    collection=collection_query(
        collection="AMZ1-WFI-L4-SR-1",
        start_date=start_date,
        end_date=end_date,
        bbox=bbox,
        bands=bands
    )   

    collection_get_data(collection)
    
    if (mosaic_method=='lcf'):
        data_dir = os.path.join(data_dir+'/'+collection)
       
        lcf_list = []
        
        for path in os.listdir(data_dir):
            scenes_list = []
            for file in os.listdir(os.path.join(data_dir, path, 'CMASK')):
                pixel_count = count_pixels_with_value(os.path.join(data_dir, path, 'CMASK', file), 127)
                scenes_list.append(dict(date=file.split("_")[3], clean_percentage=float(pixel_count['count']/pixel_count['total']), scene=path, file=''))
            for file in os.listdir(os.path.join(data_dir, path, bands[0])):
                next((item.update(file=os.path.join(data_dir, path, bands[0], file)) for item in scenes_list if item['date'] == file.split("_")[3]), None)
            sorted_data = sorted(scenes_list, key=lambda x: x['clean_percentage'], reverse=True)
            #print(sorted_data)
            lcf_list.append(sorted_data[0])
        
        tif_files = []
        for file in lcf_list:
            tif_files.append(file['file'])  
            
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file = os.path.join(output_dir, "mosaic-amazonia-brazil-2m.tif")  
        
        datasets = [rasterio.open(file) for file in tif_files]        

        extents = get_dataset_extents(datasets)
        
        merge_tifs(tif_files, output_file, extents)
        
        clipped_path = clip_raster(input_raster_path=output_file, output_folder=output_dir,clip_geometry=geom,output_filename="clipped_mosaic-amazonia-brazil-2m.tif")
