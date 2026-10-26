# CrimeDataBD — Full starter scraper

This project:
1. Reads configured newspaper XML sitemaps without recursion (queue + `while`/`for` loops).
2. Collects URLs from sitemap indexes and nested sitemap indexes.
3. Downloads article pages politely, one at a time.
4. Extracts title, date, description and article text.
5. Uses transparent rule-based patterns to identify candidate crime articles, crime types, location mentions, arrest/bail wording and CCTV camera counts.
6. Filters known publication dates to the configured range.
7. Writes CSV and JSON files, plus a CSV of errors.
8. Can optionally try geocoding location candidates.

## Project layout

```text
CrimeDataBD_Full/
├── config.py
├── main.py
├── requirements.txt
├── README.md
├── scrapers/
│   ├── __init__.py
│   ├── sitemap_crawler.py
│   ├── article_parser.py
│   ├── geocoder.py
│   └── utils.py
└── data/
```

## Windows setup

Open the folder that contains `main.py` and `config.py` in VS Code. In the terminal, ensure the current directory is that folder.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

If you already have a working virtual environment, you can reuse it. If activation is blocked by PowerShell, use the environment Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## What you should change

### Required/strongly recommended
- `config.py`: set `START_DATE` and `END_DATE`.
- `config.py`: check that both sitemap URLs are still valid. If a newspaper changes its sitemap structure, this project may need a source-specific adjustment.
- `main.py` and `scrapers/sitemap_crawler.py`: replace `replace-with-your-contact-email` in the User-Agent with a real contact email, or remove the parenthetical contact text.
- Start with `MAX_ARTICLES_PER_NEWSPAPER = 50` to test, then set it to `0` for no configured cap after you have verified behavior.

### Optional
- `CRIME_KEYWORD_FILTER = True`: keep likely crime articles only. Set `False` to save all pages found in the sitemap that pass the date filter.
- `ENABLE_GEOCODING = False`: turn on only after inspecting `location_candidates`. Geocoding uses Nominatim and can be slow; it only geocodes the first candidate location per article.
- `REQUEST_DELAY_SECONDS`: do not reduce aggressively. Respect the newspapers' terms and robots/crawl policies.

## Output files

- `data/all_sitemap_urls.csv`: URLs found in the sitemaps, including sitemap last-modified values.
- `data/crime_news_dataset.csv`: one row per candidate article.
- `data/crime_news_dataset.json`: same records as JSON.
- `data/scrape_errors.csv`: failed sitemap/article fetches and parsing errors.

Dataset columns include:
- `source_name`, `url`, `title`, `publication_date`, `description`, `article_text`
- `crime_related_candidate`, `crime_keyword_matches`, `crime_type_candidate`
- `location_candidates`
- `case_status_candidate`, `status_evidence`
- `cctv_camera_count`, `cctv_evidence`, `cctv_mentions`
- `sitemap_lastmod`
- `latitude`, `longitude`, `geocoded_query` only if geocoding is enabled

## Important limitations — read this

This is a useful **baseline**, not a verified research dataset generator. News websites change their HTML and sitemap formats. Some pages may be blocked, dynamically rendered, unavailable, or not article pages. The rule-based location extraction is intentionally conservative and incomplete; it is not proper Bangla/English named-entity recognition. Add Bangla keywords/patterns if scraping Bangla-language articles.

The fields `crime_type_candidate`, `location_candidates`, `case_status_candidate`, and `cctv_camera_count` are candidate extractions. They can be wrong or incomplete and should be manually checked or reviewed with an NLP model. In particular:
- `unknown` status means the article did not match the limited arrest/bail patterns; it does **not** mean the suspect was not caught.
- A CCTV number is filled only if a number appears close to a CCTV/security-camera phrase. It is not the number of cameras in the whole area.
- `sitemap_lastmod` is not guaranteed to be the article's publication date.
- A news article is not necessarily one unique crime incident. Multiple outlets may report the same incident, so incident-level deduplication is a separate task.
- The date filter uses article publication date where detected. Unknown dates are retained for manual review.
- The script does not make predictive claims and does not identify every crime article.

Please review each newspaper's terms, robots.txt and access policy. Do not bypass paywalls, login controls, anti-bot systems, or other access restrictions.
