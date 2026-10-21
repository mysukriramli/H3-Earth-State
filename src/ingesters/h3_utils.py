import h3

def get_h3_id(lat: float, lon: float, resolution: int = 6) -> str:
    """
    Converts a latitude/longitude point into an H3 Hexagon ID string.
    Resolution 6 = approx 36 sq km (perfect for city-scale grouping).
    """
    try:
        # h3 v4.x syntax
        return h3.latlng_to_cell(lat, lon, resolution)
    except Exception:
        return "invalid_h3"
