import posixpath
import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from config import (
    DROP_QUERY_PARAMS,
    GEOLOGY_KEYWORDS,
    TRACKING_PARAM_PREFIXES,
    UTILITY_PATH_KEYWORDS,
    UTILITY_TITLE_KEYWORDS,
)

_GEOLOGY_PATTERNS = [
    (keyword, re.compile(rf"\b{re.escape(keyword.lower())}\b"))
    for keyword in GEOLOGY_KEYWORDS
]


def safe_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def is_http_url(url: str) -> bool:
    try:
        scheme = urlsplit(url).scheme.lower()
    except ValueError:
        return False
    return scheme in {"http", "https"}


def extract_domain(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def normalize_url(url: str, base_url: str | None = None) -> str:
    if not url:
        return ""

    candidate = url.strip()
    if not candidate:
        return ""

    if base_url:
        candidate = urljoin(base_url, candidate)

    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return ""

    scheme = parsed.scheme.lower()
    if not scheme and parsed.netloc:
        scheme = "http"
    if scheme not in {"http", "https"}:
        return ""

    host = (parsed.hostname or "").lower()
    if not host:
        return ""

    port = parsed.port
    use_port = bool(
        port
        and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443))
    )
    netloc = f"{host}:{port}" if use_port else host

    path = parsed.path or "/"
    path = posixpath.normpath(path)
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    filtered_query: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower in DROP_QUERY_PARAMS:
            continue
        if any(key_lower.startswith(prefix) for prefix in TRACKING_PARAM_PREFIXES):
            continue
        filtered_query.append((key, value))
    filtered_query.sort(key=lambda kv: (kv[0].lower(), kv[1]))

    query = urlencode(filtered_query, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def is_utility_url(url: str) -> bool:
    """Return True for low-value utility pages (contact, privacy, login, etc.)."""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False

    path = (parsed.path or "").lower()
    query = (parsed.query or "").lower()

    path_tokens = re.split(r"[/\-_\.]+", path)
    query_tokens = re.split(r"[=&\-_\.]+", query)
    tokens = {token for token in (path_tokens + query_tokens) if token}
    return any(keyword in tokens for keyword in UTILITY_PATH_KEYWORDS)


def is_utility_title(title: str) -> bool:
    lowered = safe_text(title).lower()
    if not lowered:
        return False
    return any(keyword in lowered for keyword in UTILITY_TITLE_KEYWORDS)


def _keyword_stats(text: str, cap_per_keyword: int = 3) -> tuple[int, set[str]]:
    lowered = (text or "").lower()
    if not lowered:
        return 0, set()

    total_hits = 0
    matched_keywords: set[str] = set()
    for keyword, pattern in _GEOLOGY_PATTERNS:
        hits = len(pattern.findall(lowered))
        if hits <= 0:
            continue
        matched_keywords.add(keyword)
        total_hits += min(hits, cap_per_keyword)
    return total_hits, matched_keywords


def geology_score(title: str, text: str, url: str) -> int:
    """
    Weighted topical score:
    - main content drives score,
    - title/url keyword coverage boosts confidence,
    - utility pages are penalized.
    """
    text_hits, text_keywords = _keyword_stats(text, cap_per_keyword=3)
    _, title_keywords = _keyword_stats(title, cap_per_keyword=2)
    _, url_keywords = _keyword_stats(url.replace("-", " ").replace("_", " "), cap_per_keyword=2)

    coverage = len(text_keywords | title_keywords | url_keywords)
    score = text_hits + (2 * len(title_keywords)) + (2 * len(url_keywords)) + coverage

    if is_utility_url(url):
        score -= 4
    if is_utility_title(title):
        score -= 4

    return max(score, 0)


def link_priority_score(parent_score: int, anchor_text: str, target_url: str) -> int:
    """Priority hint for the frontier using link context."""
    _, anchor_keywords = _keyword_stats(anchor_text, cap_per_keyword=2)
    _, url_keywords = _keyword_stats(
        target_url.replace("-", " ").replace("_", " "),
        cap_per_keyword=2,
    )

    score = min(parent_score, 10) + (2 * len(anchor_keywords)) + len(url_keywords)
    if is_utility_url(target_url):
        score -= 5
    return max(score, 0)
