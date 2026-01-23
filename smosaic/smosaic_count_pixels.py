import numpy as np
import rasterio


def count_pixels(raster_path, target_values):
    """
    Counts the number of pixels in a raster that match specific values.
    
    Args:
        raster_path (str): Path to the raster file
        target_values (list): List of pixel values to count
        
    Returns:
        dict: Dictionary with total non-zero and non-NaN pixels and count of target values pixels
    """
    
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        
        # Create a mask for any of the target values
        mask = np.isin(data, target_values)
        count = mask.sum()
        
        valid_mask = (data != 0) & (~np.isnan(data))
        total_non_zero = valid_mask.sum()
        
        return dict(total=total_non_zero, count=count)