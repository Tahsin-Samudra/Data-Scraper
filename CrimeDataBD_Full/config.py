"""
CrimeDataBD configuration.
Edit the newspaper sitemap URLs and date range here.
Dates use YYYY-MM-DD.
"""

START_DATE = "2020-01-01"
END_DATE = "2026-10-26"

NEWSPAPERS = [
    {
        "name": "The Daily Star",
        "sitemap_url": "https://www.thedailystar.net/sitemap.xml",
        "language": "en",
    },
    {
        "name": "Prothom Alo",
        "sitemap_url": "https://en.prothomalo.com/sitemap.xml",
        "language": "en",
    },
]

REQUEST_TIMEOUT = 25
REQUEST_DELAY_SECONDS = 1.0
MAX_ARTICLES_PER_NEWSPAPER = 100  
CRIME_KEYWORD_FILTER = True

# Geocoding uses the public Nominatim service. Keep enabled only if you need coordinates.
ENABLE_GEOCODING = False
GEOCODE_COUNTRY = "Bangladesh"
GEOCODE_DELAY_SECONDS = 1.1

OUTPUT_DIR = "data"
URLS_CSV = "data/all_sitemap_urls.csv"
ARTICLES_CSV = "data/crime_news_dataset.csv"
ARTICLES_JSON = "data/crime_news_dataset.json"
ERRORS_CSV = "data/scrape_errors.csv"
