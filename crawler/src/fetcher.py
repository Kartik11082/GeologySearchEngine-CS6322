from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    BACKOFF_BASE,
    MAX_RETRIES,
    REQUEST_TIMEOUT_CONNECT,
    REQUEST_TIMEOUT_READ,
    USER_AGENT,
)


@dataclass(slots=True)
class FetchedPage:
    requested_url: str
    final_url: str | None
    status: int | None
    content_type: str
    html: str | None
    error: str | None


def create_session() -> requests.Session:
    retry = Retry(
        total=MAX_RETRIES,
        connect=MAX_RETRIES,
        read=MAX_RETRIES,
        status=MAX_RETRIES,
        backoff_factor=BACKOFF_BASE,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset({"GET", "HEAD"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_url(session: requests.Session, url: str) -> FetchedPage:
    try:
        response = session.get(
            url,
            timeout=(REQUEST_TIMEOUT_CONNECT, REQUEST_TIMEOUT_READ),
            allow_redirects=True,
        )
        content_type = response.headers.get("Content-Type", "").lower()
        html = None
        if response.status_code == 200 and "text/html" in content_type:
            html = response.text

        return FetchedPage(
            requested_url=url,
            final_url=response.url,
            status=response.status_code,
            content_type=content_type,
            html=html,
            error=None,
        )
    except requests.RequestException as exc:
        return FetchedPage(
            requested_url=url,
            final_url=None,
            status=None,
            content_type="",
            html=None,
            error=str(exc),
        )
