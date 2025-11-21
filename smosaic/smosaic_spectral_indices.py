import os
import re
import subprocess

def ndvi_calc(nir, red, compress='LZW'):
    output_ndvi_file = nir.replace("-B08-", "-NDVI-")
    os.system(f'gdal_calc.py -A {nir} -B {red} --outfile={output_ndvi_file} --calc="where((A+B)==0,-9999,(A-B)/(A+B))" --type=Float32 --NoDataValue=-9999 --co COMPRESS={compress} --co BIGTIFF=IF_SAFER')

def evi_calc(nir, red, blue, compress='LZW'):
    output_evi_file = nir.replace("-B08-", "-EVI-")
    os.system(f'gdal_calc.py -A {nir} -B {red} -C {blue} --outfile={output_evi_file} --calc="where((A + 6.0 * B - 7.5 * C + 1.0) == 0, -9999, 2.5 * (A - B) / (A + 6.0 * B - 7.5 * C + 1.0))" --type=Float32 --NoDataValue=-9999 --co COMPRESS={compress} --co BIGTIFF=IF_SAFER')

def evi2_calc(nir, red, compress='LZW'):
    output_evi2_file = nir.replace("-B08-", "-EVI2-")
    os.system(f'gdal_calc.py -A {nir} -B {red} --outfile={output_evi2_file} --calc="2.5 * where((A + 2.4 * B + 1.0) == 0, -9999, (A - B) / (A + 2.4 * B + 1.0))" --type=Float32 --NoDataValue=-9999 --co COMPRESS={compress} --co BIGTIFF=IF_SAFER')

def savi_calc(nir, red, compress='LZW'):
    output_savi_file = nir.replace("-B08-", "-SAVI-")
    os.system(f'gdal_calc.py -A {nir} -B {red} --outfile={output_savi_file} --calc="where((A + B + 0.5) == 0, -9999, (1.5 * (A - B)) / (A + B + 0.5))" --type=Float32 --NoDataValue=-9999 --co COMPRESS={compress} --co BIGTIFF=IF_SAFER')

def get_raster_dimensions(filename):
    cmd = f'gdalinfo {filename}'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        return None, None
    
    for line in result.stdout.split('\n'):
        if 'Size is' in line:
            dims_str = line.split('Size is ')[1].strip()
            dims_str = dims_str.replace('(', '').replace(')', '')
            dims = dims_str.split(', ')
            width = int(dims[0].strip(','))
            height = int(dims[1].strip(','))
            return width, height
    return None, None

def ndbi_calc(band_1, band_2, compress='LZW'):
    
    output_file = band_2.replace("-B08-", "-NDBI-")
    
    dims_band_1 = get_raster_dimensions(band_1)
    dims_band_2 = get_raster_dimensions(band_2)
    
    if dims_band_1 is None or dims_band_2 is None:
        return
    
    band_1_resampled = band_1
    band_2_resampled = band_2
    
    if dims_band_1 != dims_band_2:
        valid_widths = [d for d in [dims_band_1[0], dims_band_2[0]] if d is not None]
        valid_heights = [d for d in [dims_band_1[1], dims_band_2[1]] if d is not None]
        
        if not valid_widths or not valid_heights:
            return
            
        target_width = max(valid_widths)
        target_height = max(valid_heights)
        
        if dims_band_1[0] != target_width or dims_band_1[1] != target_height:
            temp_band_1_resampled = f"temp_resampled_band_1_{os.path.basename(band_1)}"
            resample_cmd_band_1 = f'gdalwarp -ts {target_width} {target_height} -r bilinear {band_1} {temp_band_1_resampled}'
            os.system(resample_cmd_band_1)
            band_1_resampled = temp_band_1_resampled
        
        if dims_band_2[0] != target_width or dims_band_2[1] != target_height:
            temp_band_2_resampled = f"temp_resampled_band_2_{os.path.basename(band_2)}"
            resample_cmd_band_2 = f'gdalwarp -ts {target_width} {target_height} -r bilinear {band_2} {temp_band_2_resampled}'
            os.system(resample_cmd_band_2)
            band_2_resampled = temp_band_2_resampled
    
    os.system(f'gdal_calc.py -A {band_1_resampled} -B {band_2_resampled} --outfile={output_file} --calc="where((A+B)==0,-9999,(A-B)/(A+B))" --type=Float32 --NoDataValue=-9999 --co COMPRESS={compress} --co BIGTIFF=IF_SAFER')
    
    if band_1_resampled != band_1 and os.path.exists(band_1_resampled):
        os.remove(band_1_resampled)
    if band_2_resampled != band_2 and os.path.exists(band_2_resampled):
        os.remove(band_2_resampled)
   
def mndwi_calc(band_1, band_2, compress='LZW'):
    pass

def calculate_spectral_indices(input_folder: str, spectral_indices) -> str:
    for spectral_indice in spectral_indices:

        if spectral_indice == "NDVI":
            pattern_nir = r'-B08-'
            files_nir = [
                os.path.join(input_folder, f) for f in os.listdir(input_folder)
                if re.search(pattern_nir, f)
            ]
            
            pattern_red = r'-B04-'
            files_red = [
                os.path.join(input_folder, f) for f in os.listdir(input_folder)
                if re.search(pattern_red, f)
            ]

            for i in range(min(len(files_nir), len(files_red))):
                ndvi_calc(files_nir[i], files_red[i])
        
        if spectral_indice == "EVI":
            pattern_nir = r'-B08-'
            files_nir = [
                os.path.join(input_folder, f) for f in os.listdir(input_folder)
                if re.search(pattern_nir, f)
            ]
            
            pattern_red = r'-B04-'
            files_red = [
                os.path.join(input_folder, f) for f in os.listdir(input_folder)
                if re.search(pattern_red, f)
            ]

            pattern_blue = r'-B02-'
            files_blue = [
                os.path.join(input_folder, f) for f in os.listdir(input_folder)
                if re.search(pattern_blue, f)
            ]
            
            for i in range(min(len(files_nir), len(files_red))):
                evi_calc(files_nir[i], files_red[i], files_blue[i])
        
        if spectral_indice == "EVI2":
            pattern_nir = r'-B08-'
            files_nir = [
                os.path.join(input_folder, f) for f in os.listdir(input_folder)
                if re.search(pattern_nir, f)
            ]
            
            pattern_red = r'-B04-'
            files_red = [
                os.path.join(input_folder, f) for f in os.listdir(input_folder)
                if re.search(pattern_red, f)
            ]

            for i in range(min(len(files_nir), len(files_red))):
                evi2_calc(files_nir[i], files_red[i])
        
        if spectral_indice == "SAVI":
            pattern_nir = r'-B08-'
            files_nir = [
                os.path.join(input_folder, f) for f in os.listdir(input_folder)
                if re.search(pattern_nir, f)
            ]
            
            pattern_red = r'-B04-'
            files_red = [
                os.path.join(input_folder, f) for f in os.listdir(input_folder)
                if re.search(pattern_red, f)
            ]

            for i in range(min(len(files_nir), len(files_red))):
                savi_calc(files_nir[i], files_red[i])
        
        if spectral_indice == "NDBI":
            pattern_swir = r'-B11-'
            files_swir = [
                os.path.join(input_folder, f) for f in os.listdir(input_folder)
                if re.search(pattern_swir, f)
            ]
            
            pattern_nir = r'-B08-'
            files_nir = [
                os.path.join(input_folder, f) for f in os.listdir(input_folder)
                if re.search(pattern_nir, f)
            ]
            
            for i in range(min(len(files_swir), len(files_nir))):
                ndbi_calc(band_1=files_swir[i],band_2=files_nir[i],indice="NDBI")
                        
        if spectral_indice == "MNDWI":
            pass