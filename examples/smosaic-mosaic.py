import os
from smosaic import mosaic

stac_url = "https://data.inpe.br/bdc/stac/v1"

result = mosaic(
    name="MT",
    data_dir=os.path.abspath(""),
    stac_url=stac_url,
    collection="S2_L2A-1",
    grid="BDC_SM_V2",
    tile_id="020019",
    projection_output="BDC",
    output_dir=os.path.join("output"),   
    mosaic_method="lcf", 
    start_year=2026,
    start_month=1,
    start_day=1,
    duration_days=16, 
    bands=["B02","B03","B04"]
)