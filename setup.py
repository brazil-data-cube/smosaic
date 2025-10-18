import os
from setuptools import find_packages, setup

DIR = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(DIR, "VERSION"), "r") as file:
    VERSION = file.read()

with open(os.path.join(DIR, "README.rst"), "r") as file:
    LONG_DESCRIPTION = file.read()

long_description = LONG_DESCRIPTION,

setup(
    name='smosaic',
    packages=find_packages(),
    package_data={
        "smosaic": ["config/*.json", "config/*.geojson"],
    },
    include_package_data=True,
    version = VERSION,
    description='Simple python package for creating satellite image mosaics based on Brazil Data Cube',
    author='Gabriel Sansigolo',
    author_email = "gabrielsansigolo@gmail.com",
    url = "https://github.com/GSansigolo/smosaic",
    install_requires= [
        "numpy==2.3.4",
        "tqdm==4.67.1",
        "pyproj==3.7.2",
        "shapely==2.1.2",
        "requests==2.32.5",
        "GDAL==3.11.4",
        "rasterio==1.4.3",
        "pystac-client==0.9.0",
    ],
    long_description = LONG_DESCRIPTION,
    setup_requires=['pytest-runner'],
    tests_require=['pytest==4.4.1'],
    test_suite='tests',
)