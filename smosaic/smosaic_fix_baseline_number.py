import os
import rasterio

def fix_baseline_number(input_folder: str, input_filename: str, baseline_number: str) -> str:
    """
    Adjust image value based on the baseline number in a file's naming .
    
    Args:
        input_folder (str): Directory path containing the input file.
        input_filename (str): Name of the input file to be processed.
        baseline_number (str): Baseline number to assign or correct in the file.
    
    Returns:
        str: Path or identifier of the processed file with the updated baseline number.
    """
    input_file = os.path.join(input_folder, f'{input_filename}.tif')

    with rasterio.open(input_file) as src:
        image_data = src.read()  
        profile = src.profile  
        height, width = src.shape  

    if int(baseline_number) > 400:

        new_image_data = image_data.astype('int16') - 1000
        
        profile.update({
            'dtype': 'int16'
        })

        with rasterio.open(input_file, 'w', **profile) as dst:
            dst.write(new_image_data)
            

    return True