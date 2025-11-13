import os
from smosaic import mosaic

stac_url = "https://data.inpe.br/bdc/stac/v1"

result = mosaic(
    name="luis-eduardo-magalhaes",
    data_dir=os.path.abspath(""),
    stac_url=stac_url,
    collection="S2_L2A-1", 
    bbox="-46.5848,-12.3534,-45.6482,-11.4248",
    output_dir=os.path.join("output"),   
    mosaic_method="lcf", 
    start_year=2025,
    start_month=5,
    start_day=25,
    duration_days=16, 
    bands=["B02","B03","B04"]
)

