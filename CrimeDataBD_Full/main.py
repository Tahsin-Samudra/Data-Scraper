import csv
import json
import os
import time
import requests

from config import (
    START_DATE, END_DATE, NEWSPAPERS, REQUEST_TIMEOUT,
    REQUEST_DELAY_SECONDS, MAX_ARTICLES_PER_NEWSPAPER,
    CRIME_KEYWORD_FILTER, ENABLE_GEOCODING, OUTPUT_DIR,
    URLS_CSV, ARTICLES_CSV, ARTICLES_JSON, ERRORS_CSV
)
from scrapers.sitemap_crawler import collect_urls
from scrapers.article_parser import parse_article
from scrapers.utils import in_date_range

HEADERS = {
    "User-Agent": "CrimeDataBDResearch/1.0 (academic research; replace-with-your-contact-email)"
}
session = requests.Session()
session.headers.update(HEADERS)


def save_csv(path, records):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if not records:
        print(f"No records to save to {path}")
        return
    # Union all fields so optional geocoding columns are retained.
    fields = []
    for record in records:
        for key in record.keys():
            if key not in fields:
                fields.append(key)
    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def fetch_article(url):
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" not in content_type and content_type:
            return None, f"Not HTML (Content-Type: {content_type})"
        return response.text, ""
    except requests.RequestException as error:
        return None, str(error)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_urls = []
    errors = []

    # Stage 1: sitemap URLs
    for newspaper in NEWSPAPERS:
        try:
            records = collect_urls(newspaper)
            all_urls.extend(records)
        except Exception as error:
            errors.append({
                "stage": "sitemap",
                "source_name": newspaper.get("name", ""),
                "url": newspaper.get("sitemap_url", ""),
                "error": str(error)
            })

    # Deduplicate source + URL pairs.
    unique_urls = []
    seen = set()
    for record in all_urls:
        key = (record.get("source_name", ""), record.get("url", ""))
        if key not in seen:
            seen.add(key)
            unique_urls.append(record)

    save_csv(URLS_CSV, unique_urls)
    print(f"\nSitemap URL list saved: {URLS_CSV}")
    print(f"Total unique source URLs: {len(unique_urls)}")

    # Stage 2: fetch and parse article pages
    articles = []
    source_counts = {}
    for url_record in unique_urls:
        source_name = url_record["source_name"]
        source_counts[source_name] = source_counts.get(source_name, 0) + 1

        if MAX_ARTICLES_PER_NEWSPAPER and source_counts[source_name] > MAX_ARTICLES_PER_NEWSPAPER:
            continue

        url = url_record["url"]
        print(f"Fetching [{source_name}] {source_counts[source_name]}: {url}")
        html, error = fetch_article(url)
        if html is None:
            errors.append({
                "stage": "article_fetch",
                "source_name": source_name,
                "url": url,
                "error": error
            })
            time.sleep(REQUEST_DELAY_SECONDS)
            continue

        try:
            record = parse_article(html, url, source_name)
            record["sitemap_lastmod"] = url_record.get("sitemap_lastmod", "")

            # Use publication date for filtering when known; unknown dates are retained for review.
            if not in_date_range(record.get("publication_date", ""), START_DATE, END_DATE):
                time.sleep(REQUEST_DELAY_SECONDS)
                continue

            if CRIME_KEYWORD_FILTER and not record.get("crime_related_candidate"):
                time.sleep(REQUEST_DELAY_SECONDS)
                continue

            articles.append(record)
        except Exception as error:
            errors.append({
                "stage": "article_parse",
                "source_name": source_name,
                "url": url,
                "error": str(error)
            })

        time.sleep(REQUEST_DELAY_SECONDS)

    if ENABLE_GEOCODING and articles:
        from scrapers.geocoder import add_coordinates
        print("\nGeocoding first location candidates (may take time)...")
        articles = add_coordinates(articles)

    save_csv(ARTICLES_CSV, articles)
    with open(ARTICLES_JSON, "w", encoding="utf-8") as file:
        json.dump(articles, file, ensure_ascii=False, indent=2)

    save_csv(ERRORS_CSV, errors)

    print("\n========== COMPLETE ==========")
    print(f"Candidate crime articles: {len(articles)}")
    print(f"Article dataset CSV: {ARTICLES_CSV}")
    print(f"Article dataset JSON: {ARTICLES_JSON}")
    print(f"Errors CSV: {ERRORS_CSV}")
    print("\nReview records manually: rule-based extraction can miss facts or misclassify stories.")
    print("An article with no arrest wording is labelled 'unknown', not 'not_caught'.")


if __name__ == "__main__":
    main()
