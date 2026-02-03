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


Installation
============

``smosaic`` depends essentially on `Requests <https://requests.readthedocs.io/en/master/>`_ and several geospatial libraries. Please, read the instructions below in order to install ``smosaic``.

User Installation
-----------------

The easiest way to install ``smosaic`` is using ``pip``::

    pip install smosaic


Conda Environment Installation
------------------------------

If you prefer using **Conda**, follow these steps to create a dedicated environment and install the necessary dependencies:

**1. Create and Activate the Environment**

Create a new environment named ``smosaic`` with Python 3.11::

    conda create -n smosaic python=3.11 -y
    conda activate smosaic

**2. Install Core and Documentation Dependencies**

Install the primary packages from the ``conda-forge`` channel::

    conda install -c conda-forge \
      numpy=2.3.4 \
      gdal \
      pyproj=3.7.2 \
      shapely=2.1.2 \
      rasterio=1.4.3 \
      tqdm=4.67.1 \
      requests=2.32.5 \
      pystac-client=0.9.0 \
      sphinx=8.2.3 \
      sphinx-rtd-theme=3.0.2 \
      docutils=0.21.2 \
      pygments=2.19.2 \
      jinja2=3.1.6 \
      babel=2.17.0 \
      certifi=2026.1.4 \
      charset-normalizer=3.4.4 \
      idna=3.11 \
      imagesize=1.4.1 \
      packaging=25.0 \
      snowballstemmer=3.0.1 \
      urllib3=2.6.3 \
      build \
      -y

**3. Install Sphinx Extensions via Pip**

Some specific documentation plugins should be installed via ``pip`` within the conda environment::

    pip install \
      "myst-parser>=4.0.0,<4.1" \
      "sphinx-copybutton>=0.5.2,<1.0.0" \
      "sphinx-design>=0.6.1,<0.7" \
      "sphinx-colorschemed-images>=0.2.0" \
      "sphinx-nefertiti==0.9.1" \
      "roman-numerals==4.1.0" \
      "roman-numerals-py==4.1.0"


Development Installation
------------------------

Clone the Software Repository::

    git clone https://github.com/brazil-data-cube/smosaic

Go to the source code folder::

    cd smosaic

Install in development mode::

    pip3 install -e .[all]


.. note::

    If you want to create a new *Python Virtual Environment* without Conda, please, follow this instruction:

    **1.** Create a new virtual environment linked to Python 3.11::

        python3.11 -m venv venv

    **2.** Activate the new environment::

        source venv/bin/activate

    **3.** Update pip and setuptools::

        pip3 install --upgrade pip
        pip3 install --upgrade setuptools

Run the Tests
+++++++++++++

WIP

Build the Documentation
+++++++++++++++++++++++

You can generate the documentation based on Sphinx with the following command::

    sphinx-build docs/sphinx docs/sphinx/_build/html

The above command will generate the documentation in HTML and it will place it under::

    docs/sphinx/_build/html/

You can open the above documentation in your favorite browser, as::

    firefox docs/sphinx/_build/html/index.html