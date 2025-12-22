import pyproj
import shapely

from osgeo import gdal
from shapely.ops import transform as shapely_transform

gdal.PushErrorHandler('CPLQuietErrorHandler')
gdal.UseExceptions()  

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
