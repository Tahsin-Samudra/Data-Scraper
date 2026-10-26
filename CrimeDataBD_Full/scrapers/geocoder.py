import time
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

from config import GEOCODE_COUNTRY, GEOCODE_DELAY_SECONDS


def add_coordinates(records):
    """Add coordinates for location candidates. Geocoding is approximate; review results."""
    geolocator = Nominatim(user_agent="CrimeDataBDResearch/1.0 (replace-with-contact-email)")
    geocode = RateLimiter(
        geolocator.geocode,
        min_delay_seconds=GEOCODE_DELAY_SECONDS,
        swallow_exceptions=True
    )

    cache = {}
    for index, record in enumerate(records, start=1):
        raw_location = record.get("location_candidates", "").split(";")[0].strip()
        if not raw_location:
            record["latitude"] = ""
            record["longitude"] = ""
            record["geocoded_query"] = ""
            continue

        query = f"{raw_location}, {GEOCODE_COUNTRY}"
        if query not in cache:
            result = geocode(query)
            cache[query] = result

        result = cache[query]
        record["geocoded_query"] = query
        record["latitude"] = result.latitude if result else ""
        record["longitude"] = result.longitude if result else ""
        if index % 25 == 0:
            print(f"  Geocoding progress: {index}/{len(records)}")
    return records
