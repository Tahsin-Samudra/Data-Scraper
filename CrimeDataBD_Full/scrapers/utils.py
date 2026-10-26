import re
from datetime import datetime
from dateutil import parser as date_parser


def clean_text(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_date(value):
    """Return YYYY-MM-DD when a date can be parsed, otherwise an empty string."""
    if not value:
        return ""
    try:
        parsed = date_parser.parse(str(value), fuzzy=True)
        return parsed.date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return ""


def in_date_range(date_string, start_date, end_date):
    """Unknown dates are kept for review; known dates are filtered inclusively."""
    if not date_string:
        return True
    try:
        value = datetime.strptime(date_string, "%Y-%m-%d").date()
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        return start <= value <= end
    except ValueError:
        return True
