from dataclasses import dataclass

from bs4 import BeautifulSoup

from utils import is_http_url, normalize_url, safe_text


@dataclass(slots=True)
class ParsedPage:
    title: str
    clean_text: str
    outlinks: list[str]
    anchor_map: dict[str, str]


def parse_html(html: str, base_url: str) -> ParsedPage:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = safe_text(soup.title.string)

    clean_text = safe_text(soup.get_text(" ", strip=True))

    outlinks: list[str] = []
    anchor_map: dict[str, str] = {}
    seen_outlinks: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        if not href:
            continue

        lowered = href.lower()
        if lowered.startswith(("mailto:", "javascript:", "tel:", "data:")):
            continue

        normalized = normalize_url(href, base_url=base_url)
        if not normalized or not is_http_url(normalized):
            continue
        if normalized in seen_outlinks:
            continue

        seen_outlinks.add(normalized)
        outlinks.append(normalized)
        anchor_map[normalized] = safe_text(anchor.get_text(" ", strip=True))

    return ParsedPage(
        title=title,
        clean_text=clean_text,
        outlinks=outlinks,
        anchor_map=anchor_map,
    )
