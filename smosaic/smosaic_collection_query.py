
def collection_query(collection, start_date, end_date, tile=None, bbox=None, freq=None, bands=None):
    return dict(
        collection = collection,
        bands = bands,
        start_date = start_date,
        tile = tile,
        bbox = bbox,
        end_date = end_date
    )
