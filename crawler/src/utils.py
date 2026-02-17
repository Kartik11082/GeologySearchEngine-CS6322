import posixpath
import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from config import DROP_QUERY_PARAMS, GEOLOGY_KEYWORDS, TRACKING_PARAM_PREFIXES


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


def geology_score(title: str, text: str, url: str) -> int:
    blob = f"{title}\n{text}\n{url}".lower()
    return sum(blob.count(keyword) for keyword in GEOLOGY_KEYWORDS)
