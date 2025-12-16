import os
from smosaic import mosaic

stac_url = "https://data.inpe.br/bdc/stac/v1"

result = mosaic(
    name="sao-paulo",
    data_dir=os.path.abspath(""),
    stac_url=stac_url,
    collection="S2_L2A-1", 
    bbox="-46.9089,-23.8218,-46.3692,-23.2767",
    output_dir=os.path.join("output"),   
    mosaic_method="lcf", 
    start_year=2025,
    start_month=6,
    start_day=1,
    duration_months=1, 
    end_year=2025,
    end_month=7,
    end_day=31,
    bands=["B02","B03","B04"],
)