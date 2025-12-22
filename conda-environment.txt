# Create environment with Python 3.11
conda create -n smosaic python=3.11 -y
conda activate smosaic

# Install the packages
conda install -c conda-forge numpy=2.3.4 -y
conda install -c conda-forge gdal -y
conda install -c conda-forge tqdm=4.67.1 -y
conda install -c conda-forge pyproj=3.7.2 -y
conda install -c conda-forge shapely=2.1.2 -y
conda install -c conda-forge requests=2.32.5 -y
conda install -c conda-forge rasterio=1.4.3 -y
conda install -c conda-forge pystac-client=0.9.0 -y
conda install -c conda-forge build -y

