import pyproj
import shapely

from osgeo import gdal
from shapely.ops import transform as shapely_transform

from smosaic.smosaic_utils import get_coverage_projection

gdal.PushErrorHandler('CPLQuietErrorHandler')
gdal.UseExceptions()  

def get_dataset_extents(datasets, projection_output):
    extents = []
    for ds in datasets:

        left, bottom, right, top = ds.bounds
        
        extent = shapely.geometry.box(left, bottom, right, top)
        
        data_proj = ds.crs
        if(projection_output=='BDC'):
            proj_bdc = get_coverage_projection()
            proj_converter = pyproj.Transformer.from_crs(data_proj, proj_bdc, always_xy=True).transform
        else:
            proj_converter = pyproj.Transformer.from_crs(data_proj, pyproj.CRS.from_epsg(projection_output), always_xy=True).transform
        
        reproj_bbox = shapely_transform(proj_converter, extent)
        
        extents.append(reproj_bbox)
        
    return shapely.geometry.MultiPolygon(extents).bounds
