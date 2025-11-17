import os
import tqdm
import rasterio

from rasterio.errors import RasterioIOError

def verify_tif_integrity(file_path):
    try:
        with rasterio.open(file_path) as src:
            sample_data = src.read(1, window=((0, min(100, src.height)), (0, min(100, src.width))))
            if src.width > 0 and src.height > 0 and src.count > 0:
                return True
            return False
    except (RasterioIOError, Exception) as e:
        print(f"Corrupted file detected: {file_path} - Error: {e}")
        return False
    

def download_stream(file_path: str, response, chunk_size=1024*64, progress=True, offset=0, total_size=None):
    """Download request stream data to disk.

    Args:
        file_path - Absolute file path to save
        response - HTTP Response object
    """
    parent = os.path.dirname(file_path)

    if parent:
        os.makedirs(parent, exist_ok=True)

    if not total_size:
        total_size = int(response.headers.get('Content-Length', 0))

    file_name = os.path.basename(file_path)

    progress_bar = tqdm.tqdm(
        desc=file_name[:30]+'... ',
        total=total_size,
        unit="B",
        unit_scale=True,
        #disable=not progress,
        initial=offset,
        disable=True
    )

    mode = 'a+b' if offset else 'wb'

    with response:
        with open(file_path, mode) as stream:
            for chunk in response.iter_content(chunk_size):
                stream.write(chunk)
                progress_bar.update(chunk_size)

    file_size = os.stat(file_path).st_size

    if file_size != total_size:
        os.remove(file_path)
        raise IOError(f'Download file is corrupt. Expected {total_size} bytes, got {file_size}')
    
    if file_path.lower().endswith(('.tif', '.tiff')):
        if not verify_tif_integrity(file_path):
            os.remove(file_path)
            raise IOError(f'Downloaded TIFF file is corrupted: {file_path}')