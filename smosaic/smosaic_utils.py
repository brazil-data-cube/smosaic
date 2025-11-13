import os
import json
import pyproj
import shapely
import dateutil
import datetime
import importlib
from pathlib import Path
from typing import Any, Dict

CLOUD_CONFIG = {
    'S2-16D-2': {
        'cloud_band': 'SCL',
        'non_cloud_values': [4, 5, 6],
        'cloud_values': [0, 1, 2, 3, 7, 8, 9, 10, 11],
        'no_data_value': 0
    },
    'S2_L2A-1': {
        'cloud_band': 'SCL',
        'non_cloud_values': [4, 5, 6],
        'cloud_values': [0, 1, 2, 3, 7, 8, 9, 10, 11],
        'no_data_value': 0
    }
}

COVERAGE_PROJ = pyproj.CRS.from_wkt('''
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

# Cache for loaded JSON data
_json_cache = {}

def load_json_config(file_path: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Load JSON configuration from a file with optional caching.
    
    Args:
        file_path: Path to the JSON file
        use_cache: If True, cache the result for subsequent calls
        
    Returns:
        Dictionary containing the JSON data
    """
    global _json_cache
    
    # Convert to absolute path for consistent caching
    abs_path = str(Path(file_path).resolve())
    
    if use_cache and abs_path in _json_cache:
        return _json_cache[abs_path].copy()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
        if use_cache:
            _json_cache[abs_path] = data
            
        return data.copy() if isinstance(data, dict) else data
    except FileNotFoundError:
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {file_path}: {e}")


def get_all_cloud_configs() -> Dict[str, Dict[str, Any]]:
    """
    Get all cloud configurations.
    
    Returns:
        Dictionary of all cloud configurations
    """
    return {k: v.copy() for k, v in CLOUD_CONFIG.items()}


def get_coverage_projection() -> pyproj.CRS:
    """
    Get the coverage projection CRS.
    
    Returns:
        pyproj.CRS object for the coverage projection
    """
    return COVERAGE_PROJ


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


def days_between_dates(date1, date2):
    """
    Calculate the number of days between two dates.
    
    Args:
        date1 (str): First date in 'YYYY-MM-DD' format
        date2 (str): Second date in 'YYYY-MM-DD' format
    
    Returns:
        int: Number of days between the two dates (positive if date2 is after date1, negative if date2 is before date1)
    """
    d1 = datetime.datetime.strptime(date1, '%Y-%m-%d')
    d2 = datetime.datetime.strptime(date2, '%Y%m%d')
    
    return abs((d2 - d1).days)


def add_days_to_date(start_date, days_to_add):
    """
    Add a specified number of days to a given date.
    
    Args:
        start_date (datetime/str): The starting date.
        days_to_add (int): The number of days to add (positive or negative).
    
    Returns:
        datetime: The new date after adding the specified number of days.
    """
    if isinstance(start_date, str):
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    
    return start_date + dateutil.relativedelta.relativedelta(days=days_to_add)


def find_grid_by_name(grid_name):

	bdc_grids_data = load_jsons("grids")

	for grid in bdc_grids_data.get("grids", []):

		if grid.get("name") == grid_name:

			return grid
        
	return None


def geometry_collides_with_bbox(geometry,input_bbox):

    bbox_polygon = shapely.geometry.box(*input_bbox)

    return geometry.intersects(bbox_polygon)


def clean_dir(data_dir):
    files_to_delete = [
        os.path.join(data_dir, f) 
        for f in os.listdir(data_dir)  #f.startswith("merge_") or
        if  f.startswith("temp_") or f.startswith("provenance_") or f.startswith("clear_") or f.startswith("cloud_")
    ]
    
    for f in files_to_delete:
        try:
            os.remove(f)
        except:
            pass
