#
# This file is part of Brazil Data Cube Documentation.
# Copyright 2026 INPE.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
#

import sphinx_rtd_theme
import sphinx_nefertiti

import os
import sys

sys.path.insert(0, os.path.abspath("../.."))



# -- Project information -----------------------------------------------------

project = 'smosaic'
copyright = 'GNU General Public License, v3.0.'
author = "Brazil Data Cube (BDC)"
# release = smosaic.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

autodoc_mock_imports = [
    "osgeo",
    "osgeo.gdal",
]


extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx_copybutton',
    'sphinx_design',
    "sphinx_rtd_theme",
    'sphinx_colorschemed_images',
    "sphinx_nefertiti",
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_nefertiti"
html_static_path = ['_static']

html_theme_options = {
    "sans_serif_font": "Ubuntu Sans",
    "documentation_font": "Open Sans",
    "monospace_font": "Fira Code",
    "project_name_font": "Nunito",
    "doc_headers_font": "Georgia",
    "documentation_font_size": "1.3rem",
    "monospace_font_size": "1.2rem",
    "style": "blue",
    "pygments_light_style": "pastie",
    "pygments_dark_style": "dracula",
    "header_links": [
        {
            "text": "Índice",
            "link": "index",
        },
        # {
        #     "text": "Tutoriais",
        #     "dropdown": [
        #         {"text": "Geoserver", "link": "geoserver/index"},
        #         # {"text": "Infra", "link": "infra/index"},
        #     ],
        # },
        {
            "text": "BIG",
            "link": "https://data.inpe.br/",
            "target": "_blank",
        },
        {
            "text": "BDC",
            "link": "https://data.inpe.br/bdc/",
            "target": "_blank",
        },
        {
            "text": "Links",
            "link": "links",
        },
    ],
    "logo": "logo-bdc.svg",
    "logo_width": 65,
    "logo_height": 65,
    "logo_alt": "BDC/INPE",
    "footer_links": [
        {
            "text": "Documentação BDC",
            "link": "https://brazil-data-cube.github.io/index.html",
        },
        {
            "text": "GitHub",
            "link": "https://github.com/brazil-data-cube/",
        },
        {
            "text": "Discord",
            "link": "https://discord.gg/enS8GdY6",
        },
    ],

    "repository_url": "https://github.com/brazil-data-cube/smosaic",
    "repository_name": "smosaic",

    "docs_repository_url": "https://github.com/brazil-data-cube/smosaic/tree/main/docs/sphinx/",
}


html_css_files = [
    "custom.css",
]

html_logo = "_static/logo-bdc.png"

html_favicon = "_static/favicon.ico"

