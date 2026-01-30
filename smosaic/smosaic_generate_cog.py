import os

from osgeo import gdal

gdal.PushErrorHandler('CPLQuietErrorHandler')
gdal.UseExceptions()  

def generate_cog(input_folder: str, input_filename: str, compress: str = 'LZW') -> str:
    """Generate COG file."""
    input_file = os.path.join(input_folder, f'{input_filename}.tif')
    output_file = os.path.join(input_folder, f'{input_filename}_COG.tif')

    gdal.Translate(
        output_file,
        input_file,
        options=gdal.TranslateOptions(
            format='COG',
            creationOptions=[
                f'COMPRESS={compress}',
                'BLOCKSIZE=256',
                'BIGTIFF=IF_SAFER'
            ],
            outputType=gdal.GDT_Int16
        )
    )

    print(f"Raster saved to: {output_file}")
    
    return output_file
