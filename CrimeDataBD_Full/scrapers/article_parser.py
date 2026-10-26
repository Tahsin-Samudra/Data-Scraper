import json
import re
from bs4 import BeautifulSoup
from scrapers.utils import clean_text, parse_date

# These are candidate keywords, not a perfect crime classifier.
CRIME_KEYWORDS = [
    "murder", "killed", "kill", "rape", "raped", "robbery", "robbed",
    "theft", "stolen", "kidnap", "kidnapped", "abduction", "assault",
    "attack", "clash", "arrested", "detained", "fraud", "scam", "extortion",
    "drug", "smuggling", "human trafficking", "cybercrime", "burglary",
    "shooting", "shot dead", "body found", "dead body", "police case",
    "accused", "suspect", "court", "sentenced", "rape case", "gang"
]

CRIME_TYPE_PATTERNS = [
    ("murder", r"\b(murder|murdered|killed|shot dead|homicide)\b"),
    ("rape/sexual violence", r"\b(rape|raped|sexual assault|sexual violence)\b"),
    ("robbery", r"\b(robbery|robbed|armed robbery|snatched|snatching)\b"),
    ("theft/burglary", r"\b(theft|stolen|burglary|burglar|housebreaking)\b"),
    ("kidnapping", r"\b(kidnap|kidnapped|kidnapping|abducted|abduction)\b"),
    ("assault/attack", r"\b(assault|attacked|attack|beaten|beating)\b"),
    ("fraud/scam", r"\b(fraud|scam|cheated|forgery|embezzlement)\b"),
    ("extortion", r"\b(extortion|extorted|toll collection)\b"),
    ("drug crime", r"\b(drug trafficking|drug smuggling| yaba|narcotics|drug dealer)\b"),
    ("human trafficking", r"\b(human trafficking|trafficked)\b"),
    ("cybercrime", r"\b(cybercrime|phishing|hacking|online fraud)\b"),
    ("smuggling", r"\b(smuggling|smuggled)\b"),
    ("corruption", r"\b(corruption|bribe|bribery|money laundering)\b"),
    ("clash/violence", r"\b(clash|violence|violent attack|riot)\b"),
]

# Specificity-oriented patterns. Results are candidate locations to manually verify.
LOCATION_PATTERNS = [
    r"\b(Mirpur(?:-\s?\d+)?(?:-\s?\d+)?|Dhanmondi(?:\s+\d+)?|Bashundhara(?:\s+R\/A)?|Gulshan(?:-\s?\d+)?|Banani|Uttara(?:\s+(?:Sector|sector)\s*\d+)?|Mohammadpur|Motijheel|Old Dhaka|Farmgate|Tejgaon|Rampura|Badda|Jatrabari|Shahbagh|Paltan|Khilgaon|Lalbagh|Kafrul|Pallabi|Demra|Keraniganj|Savar|Ashulia|Gazipur|Narayanganj|Chattogram|Chittagong|Sylhet|Rajshahi|Khulna|Barishal|Rangpur|Cumilla|Comilla|Cox'?s Bazar)\b",
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z0-9-]+){0,3}\s+(?:Road|Street|Lane|Avenue|Bridge|Bazar|Market|Circle|Square|Gate|Residential Area))\b"
]

def get_meta(soup, selectors):
    for attr, value in selectors:
        tag = soup.find("meta", attrs={attr: value})
        if tag and tag.get("content"):
            return clean_text(tag["content"])
    return ""


def extract_article_date(soup, jsonld_objects):
    candidates = [
        get_meta(soup, [("property", "article:published_time"),
                        ("name", "pubdate"),
                        ("name", "publishdate"),
                        ("name", "date"),
                        ("itemprop", "datePublished")])
    ]
    for obj in jsonld_objects:
        if isinstance(obj, dict):
            for key in ("datePublished", "dateCreated", "dateModified"):
                if obj.get(key):
                    candidates.append(str(obj[key]))
    for candidate in candidates:
        parsed = parse_date(candidate)
        if parsed:
            return parsed
    time_tag = soup.find("time")
    if time_tag:
        return parse_date(time_tag.get("datetime") or time_tag.get_text(" ", strip=True))
    return ""


def flatten_jsonld(value, results):
    if isinstance(value, dict):
        results.append(value)
        for item in value.values():
            flatten_jsonld(item, results)
    elif isinstance(value, list):
        for item in value:
            flatten_jsonld(item, results)


def parse_article(html, url, source_name):
    soup = BeautifulSoup(html, "lxml")
    jsonld_objects = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            flatten_jsonld(json.loads(script.string or script.get_text()), jsonld_objects)
        except (json.JSONDecodeError, TypeError):
            pass

    title = (
        get_meta(soup, [("property", "og:title"), ("name", "twitter:title")])
        or (soup.title.get_text(" ", strip=True) if soup.title else "")
    )
    description = get_meta(soup, [
        ("property", "og:description"), ("name", "description"),
        ("name", "twitter:description")
    ])

    body = None
    for selector in [
        "article", "[itemprop='articleBody']", ".article-content",
        ".story-content", ".details-content", ".content"
    ]:
        body = soup.select_one(selector)
        if body and len(body.get_text(" ", strip=True)) > 150:
            break
        body = None

    if body is None:
        body = soup.body or soup

    for tag in body.select("script, style, nav, footer, header, aside, form, .related, .social-share, .advertisement"):
        tag.decompose()

    paragraphs = []
    for paragraph in body.find_all(["p", "h2", "h3"]):
        text = clean_text(paragraph.get_text(" ", strip=True))
        if len(text) > 25:
            paragraphs.append(text)
    article_text = clean_text(" ".join(paragraphs))
    if len(article_text) < 80:
        article_text = clean_text(body.get_text(" ", strip=True))

    combined = clean_text(f"{title}. {description}. {article_text}")
    low = combined.lower()

    crime_matches = [keyword for keyword in CRIME_KEYWORDS if keyword in low]
    crime_related = bool(crime_matches)

    crime_types = []
    for label, pattern in CRIME_TYPE_PATTERNS:
        if re.search(pattern, low, flags=re.IGNORECASE):
            crime_types.append(label)

    locations = []
    for pattern in LOCATION_PATTERNS:
        for match in re.findall(pattern, combined, flags=re.IGNORECASE):
            value = clean_text(match if isinstance(match, str) else " ".join(match))
            if value and value.lower() not in [x.lower() for x in locations]:
                locations.append(value)
    # Also capture a possible district/upazila named in the article, but avoid pretending
    # this is a complete named-entity-recognition model.
    location_text = "; ".join(locations[:8])

    status = "unknown"
    status_evidence = ""
    status_patterns = [
        ("bailed", r"\b(released on bail|granted bail|released on bond|gets bail|got bail)\b"),
        ("caught", r"\b(arrested|detained|apprehended|held in custody|taken into custody|surrendered)\b"),
        ("not_caught", r"\b(still at large|remains absconding|yet to be arrested|not arrested|fugitive)\b"),
    ]
    for candidate_status, pattern in status_patterns:
        match = re.search(pattern, low, flags=re.IGNORECASE)
        if match:
            status = candidate_status
            status_evidence = match.group(0)
            break

    cctv_mentions = re.findall(
        r".{0,50}\b(CCTV|closed-circuit television|surveillance camera|security camera)\b.{0,70}",
        combined, flags=re.IGNORECASE
    )
    cctv_number = ""
    cctv_evidence = ""
    number_patterns = [
        r"\b(\d{1,3})\s+(?:CCTV|surveillance|security)\s+cameras?\b",
        r"\b(?:CCTV|surveillance|security)\s+cameras?\s*[:=]?\s*(\d{1,3})\b"
    ]
    for pattern in number_patterns:
        match = re.search(pattern, combined, flags=re.IGNORECASE)
        if match:
            cctv_number = match.group(1)
            cctv_evidence = clean_text(match.group(0))
            break

    return {
        "source_name": source_name,
        "url": url,
        "title": clean_text(title),
        "publication_date": extract_article_date(soup, jsonld_objects),
        "description": clean_text(description),
        "article_text": article_text,
        "crime_related_candidate": crime_related,
        "crime_keyword_matches": "; ".join(crime_matches),
        "crime_type_candidate": "; ".join(crime_types) if crime_types else "unknown",
        "location_candidates": location_text,
        "case_status_candidate": status,
        "status_evidence": status_evidence,
        "cctv_camera_count": cctv_number,
        "cctv_evidence": cctv_evidence,
        "cctv_mentions": " | ".join(clean_text(x) for x in cctv_mentions[:5]),
        "extraction_note": "Rule-based candidate; verify against article text",
    }
