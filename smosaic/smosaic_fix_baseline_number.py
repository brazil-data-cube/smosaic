import os
import rasterio

def fix_baseline_number(input_folder: str, input_filename: str, baseline_number: str) -> str:

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