import time
import requests
from lxml import etree

from config import REQUEST_TIMEOUT, REQUEST_DELAY_SECONDS

HEADERS = {
    "User-Agent": "CrimeDataBDResearch/1.0 (academic research; replace-with-your-contact-email)"
}

session = requests.Session()
session.headers.update(HEADERS)


def get_root(url):
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return etree.fromstring(response.content)
    except (requests.RequestException, etree.XMLSyntaxError) as error:
        print(f"    Sitemap error: {url} | {error}")
        return None


def element_name(element):
    return etree.QName(element).localname


def read_sitemap_index_or_urlset(url):
    """Read one sitemap file. No recursive calls are used."""
    root = get_root(url)
    child_sitemaps = []
    page_records = []

    if root is None:
        return child_sitemaps, page_records

    root_type = element_name(root)

    if root_type == "sitemapindex":
        for item in root:
            child_url = item.findtext("{*}loc")
            if child_url:
                child_sitemaps.append(child_url.strip())

    elif root_type == "urlset":
        for item in root:
            page_url = item.findtext("{*}loc")
            lastmod = item.findtext("{*}lastmod")
            if page_url:
                page_records.append({
                    "url": page_url.strip(),
                    "sitemap_lastmod": lastmod.strip() if lastmod else ""
                })
    else:
        print(f"    Unexpected sitemap XML root: {root_type}")

    time.sleep(REQUEST_DELAY_SECONDS)
    return child_sitemaps, page_records


def collect_urls(newspaper):
    """
    Traverse sitemap files with a queue and while/for loops, not recursion.
    Handles multiple sitemap-index levels without recursive function calls.
    """
    name = newspaper["name"]
    start_url = newspaper["sitemap_url"]
    print(f"\n[{name}] Starting sitemap discovery")

    queue = [start_url]
    visited = set()
    records = []
    index = 0

    while index < len(queue):
        sitemap_url = queue[index]
        index += 1

        if sitemap_url in visited:
            continue
        visited.add(sitemap_url)

        children, page_records = read_sitemap_index_or_urlset(sitemap_url)

        for child_url in children:
            if child_url not in visited:
                queue.append(child_url)

        for record in page_records:
            record["source_name"] = name
            records.append(record)

        print(
            f"    Read sitemap {len(visited)} | "
            f"URLs collected so far: {len(records)}"
        )

    # Deduplicate within each newspaper while preserving original order.
    unique_records = []
    seen_urls = set()
    for record in records:
        if record["url"] not in seen_urls:
            seen_urls.add(record["url"])
            unique_records.append(record)

    print(f"[{name}] Unique URLs found: {len(unique_records)}")
    return unique_records
