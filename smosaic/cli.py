#
# This file is part of smosaic.
# Copyright (C) 2026 INPE.
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

"""Command line interface for the WLTS client."""

import click

import os
from smosaic import mosaic as run_mosaic

class Config:
    """A simple decorator class for command line options."""

    def __init__(self):
        """Initialization of Config decorator."""
        self.stac_url = None


pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group()
@click.option('--stac_url', type=click.STRING, default='https://data.inpe.br/bdc/stac/v1',
              help='The stac server address (an URL).')
@click.version_option()
@pass_config
def cli(config, stac_url):
    """smosaic on command line."""
    config.stac_url = stac_url


@cli.command()
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.option('-n', '--name',
              default='mosaic',
              show_default=True,
              help='Mosaic name')
@click.option('--data-dir',
              type=click.Path(exists=True, file_okay=False, path_type=str),
              default='.',
              show_default=True,
              help='Directory containing input data')
@click.option('--collection',
              required=True,
              help='STAC collection ID')
@click.option('--output-dir',
              type=click.Path(file_okay=False, path_type=str),
              default='output',
              show_default=True,
              help='Output directory')
@click.option('--start-year', type=int, required=True)
@click.option('--start-month', type=int, required=True)
@click.option('--start-day', type=int, required=True)
@click.option('--mosaic-method',
              type=click.Choice(['lcf', 'mean', 'median'], case_sensitive=False),
              required=True,
              help='Mosaic generation method')
@click.option('--reference-date',
              type=click.DateTime(formats=['%Y-%m-%d']),
              help='Reference date (YYYY-MM-DD)')
@click.option('--duration-days',
              type=int,
              help='Temporal window in days')
@click.option('--duration-months',
              type=int,
              help='Temporal window in months')
@click.option('--end-year', type=int)
@click.option('--end-month', type=int)
@click.option('--end-day', type=int)
@click.option("--bbox", type=click.STRING,
            help='Bounding box as "minx,miny,maxx,maxy"',
)
@click.option('--geom',
              type=click.Path(exists=True, dir_okay=False, path_type=str),
              help='Geometry file (GeoJSON / WKT)')

@click.option('--grid',
              type=click.Path(exists=True, dir_okay=False, path_type=str),
              help='Grid definition file')

@click.option('--grid-id',
              help='Grid cell identifier')
@click.option('--band',
              'bands',
              multiple=True,
              help='Band name (repeatable)')
@click.option('--profile',
              help='Processing profile')
@pass_config
def mosaic(
    config: Config,
    verbose,
    name,
    data_dir,
    collection,
    output_dir,
    start_year,
    start_month,
    start_day,
    mosaic_method,
    bands,
    reference_date,
    duration_days,
    end_year,
    end_month,
    end_day,
    duration_months,
    geom,
    grid,
    grid_id,
    bbox,
    profile,
):
    """
    Generate a spatiotemporal mosaic from a STAC collection.
    """
    if duration_days and duration_months:
        raise click.UsageError(
            'Use either --duration-days or --duration-months, not both.'
        )

    if bbox and (geom or grid):
        raise click.UsageError(
            'Use only one spatial selector: --bbox, --geom, or --grid.'
        )

    if verbose:
        click.secho(f'STAC server: {config.stac_url}', fg='cyan', bold=True)
        click.secho('Working on mosaic...', fg='cyan')

    result = run_mosaic(
        name=name,
        data_dir=data_dir,
        stac_url=config.stac_url,
        collection=collection,
        output_dir=output_dir,
        start_year=start_year,
        start_month=start_month,
        start_day=start_day,
        mosaic_method=mosaic_method,
        bands=list(bands) if bands else None,
        reference_date=reference_date.date() if reference_date else None,
        duration_days=duration_days,
        end_year=end_year,
        end_month=end_month,
        end_day=end_day,
        duration_months=duration_months,
        geom=geom,
        grid=grid,
        grid_id=grid_id,
        bbox=bbox,
        profile=profile,
    )

    if verbose:
        click.secho('Finished!', fg='green', bold=True)

    return result
