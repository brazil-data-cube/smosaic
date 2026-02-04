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


Running smosaic in the Command Line
===================================

The ``smosaic`` package installs a command line tool named ``smosaic`` that allows 
users to generate spatiotemporal mosaics from STAC-compliant data sources.


If you want to know the smosaic version, use the option ``--version``::

    smosaic --version


Mosaic command
--------------

The main command provided by the CLI is ``mosaic``, which generates a mosaic for a
given spatial extent, time range, and collection.

A minimal example is shown below::

    smosaic mosaic \
      --name sao-paulo \
      --collection S2_L2A-1 \
      --mosaic-method lcf \
      --start-year 2024 \
      --start-month 1 \
      --start-day 1 \
      --duration-months 1 \
      --bbox "-46.6507,-23.9681,-46.2772,-23.5992" \
      --band B02 \
      --band B03 \
      --band B04 \
      --profile urban_analysis
