import shapely
from shapely.geometry import box, MultiPolygon


def get_dataset_extents(datasets):
    extents = []
    for ds in datasets:
        left, bottom, right, top = ds.bounds
        extent = box(left, bottom, right, top)
        extents.append(extent)
        
    return MultiPolygon(extents).bounds