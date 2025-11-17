..
    This file is part of Python smosaic package.
    Copyright (C) 2025 INPE.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/gpl-3.0.html>.


Changes
=======

0.5.0 (2025-11-17)
------------------

* **Notebook to Script Migration**: Replaced Jupyter notebooks with Python script examples:
  - ``smosaic-closest-to-date.py``: Example of creating mosaics using closest-to-date selection
  - ``smosaic-data-cube.py``: Example of generating temporal data cubes
  - ``smosaic-mosaic.py``: General mosaic generation example
* **New Provenance Band**: Added automatic generation of provenance band indicating the origin date of each selected best pixel in the composition
* **Cloud Band Support**: Added automatic cloud band generation alongside user-requested bands
* **File Integrity Verification**: Added automatic TIFF file corruption check in ``download_stream()`` function
* **Sentinel-2 Baseline Correction**: Added new function to correct images based on Sentinel-2 processing baseline number
* **Mosaic Algorithm Refactor**: Completely redesigned ``merge_scene()`` function with improved best-pixel mosaic generation
* **Conda Environment Guide**: Added ``conda-environment.md`` documentation for creating Conda environments to install and run the library
* **Enhanced Output Bands**: All mosaic outputs now include provenance and cloud bands by default alongside requested spectral bands
* **Progress Tracking**: Enhanced library logging output with detailed progress tracking, displaying percentage completion per scene and band during mosaic generation


0.4.0 (2025-11-10)
------------------
* **New Mosaic Build Methods**: Added two new scene ordering functions for mosaic generation:
  - ``ctd`` (Closest to Date): Build mosaics by selecting images closest to a reference date
  - ``crono`` (Chronological): Build mosaics by ordering scenes by acquisition date
* **Enhanced Mosaic Function**: The ``mosaic()`` function now supports three build methods:
  - ``lcf``: Least cloud cover first (existing)
  - ``ctd``: Closest to reference date (new)
  - ``crono``: Chronological order (new)
* **New Utility Function**: Added ``days_between_dates()`` function in utils module for date interval calculations
* **New Notebook**: Added example notebook:
    * ``smosaic-closest-to-date.ipynb``: A complete example of creating Sentinel-2 image mosaic by selecting images closest to a reference date


0.3.0 (2025-10-31)
------------------

* **Architectural Refactor**: Split single file `smosaic_core.py` into modular package structure with specialized modules.
* **Breaking Changes**: 
  - All functions now distributed across dedicated modules (smosaic_clip_raster, smosaic_merge_scene, etc.)
  - Update imports to reference new modules (e.g., `from smosaic_clip_raster import clip_raster`)
* **Enhanced Mosaic Function**: Added support for monthly periods, with proper date handling.
* **New Notebook**: Added example notebook:
    * ``smosaic-monitoring-expansion-favelas-sp.ipynb``: A complete example of creating monthly Sentinel-2 image mosaics for monitoring the expansion of favelas in São Paulo.


0.2.5 (2025-10-18)
------------------

* **Fix**: Resolved an import error with `numpy`, `pyproj`, `shapely`, `requests`, `rasterio` and `pystac-client` modules.


0.2.2 (2025-10-15)
------------------

* **Fix**: Fixed a bug in the ``mosaic`` function, now it generates both single-date mosaics and data cubes correctly.


0.2.0 (2025-10-10)
------------------

* **Multi-band Support**: It is now possible to create an mosaic with more than one band.
* **Refactored Library Code**: Adjusted imports and the use of libraries in the code, removing imports of individual functions.
* **New Notebooks**: Added several example notebooks:
    * ``smosaic-introduction.ipynb``: A complete example of creating a Sentinel-2 multi-band mosaic for Luis Eduardo Magalhaes - BA.
    * ``smosaic-data-cube.ipynb``: A complete example of creating a Sentinel-2 10 days data cube for a given bbox.
* **Data Cube Support**:  Added support for data cube generation using ``end_year``, ``end_month``, ``end_day`` and ``duration_days`` parameters.
* **Refactor filter_scenes Function**: Completely refactored ``filter_scenes`` function now use the grid geometry instead of the colleciton.json file.
- **Implemented parallel processing**: to significantly speed up mosaic generation by processing multiple time steps concurrently.✨


Version 0.0.1 (2025-06-04)
------------------

* **Initial Release**: First implementation of ``mosaic`` function, with ``collection_get_data``, ``get_dataset_extents``, ``merge_tifs`` and ``clip_raster`` functions.
* Completed the smosaic exemple notebook.
* **Sentinel 2**: Added full support for Sentinel 2 data.  🛰️
* **COG Support**: Added output as Cloud Optimized GeoTIFFs (COGs) with RasterIO. 
