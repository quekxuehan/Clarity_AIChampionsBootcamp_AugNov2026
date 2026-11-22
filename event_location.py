import json
import threading
import time
from math import asin, cos, radians, sin, sqrt
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REGION_REFERENCE_POINTS = {
    "Central": (1.35735, 103.82),
    "East": (1.35735, 103.94),
    "North": (1.41803, 103.82),
    "South": (1.29587, 103.82),
    "West": (1.35735, 103.7),
}
SINGAPORE_BOUNDS = (1.15, 1.48, 103.55, 104.15)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_GEOCODING_LOCK = threading.Lock()
_LAST_GEOCODING_REQUEST = 0.0


def nearest_region(latitude: float, longitude: float) -> str | None:
    min_latitude, max_latitude, min_longitude, max_longitude = SINGAPORE_BOUNDS
    if not (
        min_latitude <= latitude <= max_latitude
        and min_longitude <= longitude <= max_longitude
    ):
        return None

    return min(
        REGION_REFERENCE_POINTS,
        key=lambda region: _distance(
            latitude,
            longitude,
            *REGION_REFERENCE_POINTS[region],
        ),
    )


def geocode_address(address: str) -> tuple[float, float] | None:
    global _LAST_GEOCODING_REQUEST

    if not address.strip():
        raise ValueError("Enter an address to search.")

    query = urlencode(
        {
            "q": address.strip(),
            "format": "jsonv2",
            "countrycodes": "sg",
            "limit": 1,
        }
    )
    request = Request(
        f"{NOMINATIM_URL}?{query}",
        headers={"User-Agent": "ClaritySG/1.0"},
    )

    with _GEOCODING_LOCK:
        delay = 1.0 - (time.monotonic() - _LAST_GEOCODING_REQUEST)
        if delay > 0:
            time.sleep(delay)
        _LAST_GEOCODING_REQUEST = time.monotonic()
        with urlopen(request, timeout=10) as response:
            results = json.loads(response.read())

    if not isinstance(results, list):
        raise ValueError("The address service returned an unexpected response.")
    if not results:
        return None
    result = results[0]
    if not isinstance(result, dict):
        raise ValueError("The address service returned an invalid result.")

    try:
        latitude = float(result["lat"])
        longitude = float(result["lon"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("The address service returned invalid coordinates.") from error

    if nearest_region(latitude, longitude) is None:
        return None
    return latitude, longitude


def _distance(
    latitude: float,
    longitude: float,
    other_latitude: float,
    other_longitude: float,
) -> float:
    latitude_delta = radians(other_latitude - latitude)
    longitude_delta = radians(other_longitude - longitude)
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(radians(latitude))
        * cos(radians(other_latitude))
        * sin(longitude_delta / 2) ** 2
    )
    return 2 * asin(sqrt(haversine))
