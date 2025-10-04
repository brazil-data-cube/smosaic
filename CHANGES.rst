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

0.2.0 (2025-10-01)
------------------

* **Multi-band Support**: It is now possible to create an ``xarray`` data cube with more than one band.
* **Refactored Library Code**: Adjusted imports and the use of libraries in the code, removing imports of individual functions.
* **New Notebooks**: Added several example notebooks:
    * ``smosaic-introduction.ipynb``: A complete example of creating a Sentinel-2 multi-band mosaic for Luis Eduardo Magalhaes - BA.
    * ``smosaic-data-cube.ipynb``: A complete example of creating a Sentinel-2 10 days data cube for a given bbox.
* **Data Cube Support**:  Added support for data cube generation using ``end_year``, ``end_month``, ``end_day`` and ``duration_days`` parameters.
* **Refactor Mosaic Function**: Completely refactored mosaic function to ensure the ``merge_scene`` function always work with the correct number of images. 


Version 0.0.1 (2025-06-04)
------------------

* **Initial Release**: First implementation of ``mosaic`` function, with ``collection_get_data``, ``get_dataset_extents``, ``merge_tifs`` and ``clip_raster`` functions.
* Completed the smosaic exemple notebook.
* **Sentinel 2**: Added full support for Sentinel 2 data.  🛰️
* **COG Support**: Added output as Cloud Optimized GeoTIFFs (COGs) with RasterIO. 
