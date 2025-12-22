import os
from smosaic import mosaic

stac_url = "https://data.inpe.br/bdc/stac/v1"

result = mosaic(
    name="para",
    data_dir=os.path.abspath(""),
    stac_url=stac_url,
    collection="S2_L2A-1", 
    bbox="-53.5007,-2.0485,-52.5943,-1.1288",
    output_dir=os.path.join("output"),   
    mosaic_method="lcf", 
    start_year=2025,
    start_month=1,
    start_day=1,
    duration_days=16, 
    bands=["B02","B03","B04"]
)

