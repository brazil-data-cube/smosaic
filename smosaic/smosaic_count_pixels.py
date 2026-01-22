import numpy as np
import rasterio


def count_pixels(raster_path, target_value):
    """
    Counts the number of pixels in a raster that match a specific value.
    
    Args:
        raster_path (str): Path to the raster file
        target_value (int/float): The pixel value to count
        
    Returns:
        dict: Dictionary with total non-zero and non-NaN pixels and count of target value pixels
    """
    
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        
        count = (data == target_value).sum()
        
        valid_mask = (data != 0) & (~np.isnan(data))
        total_non_zero = valid_mask.sum()
        
        return dict(total=total_non_zero, count=count)