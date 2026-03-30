"""
External Search (Google & Bing)
-------------------------------
Google: Uses Custom Search JSON API for real results.
Bing: Generates search-redirect URL (no API key).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import quote_plus

# Loaded from .env via main.py
GOOGLE_API_KEY: str = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CX: str = os.environ.get("GOOGLE_CX", "")


def _fallback_google(query: str, error: str | None = None) -> dict:
    """Fallback: return a redirect URL when API call fails."""
    result: dict = {
        "engine": "google",
        "search_url": f"https://www.google.com/search?q={quote_plus(query)}",
        "query": query,
    }
    if error:
        result["error"] = error
    return result


def google(query: str) -> list[dict] | dict:
    """
    Call Google Custom Search JSON API.
    Returns a list of result dicts matching the frontend contract,
    or a fallback dict with search_url if API is not configured / errors.
    """
    if (
        not GOOGLE_API_KEY
        or GOOGLE_API_KEY == "PASTE_YOUR_API_KEY_HERE"
        or not GOOGLE_CX
    ):
        return _fallback_google(query, "API key or CX not configured")

    url = (
        f"https://www.googleapis.com/customsearch/v1"
        f"?key={GOOGLE_API_KEY}"
        f"&cx={GOOGLE_CX}"
        f"&q={quote_plus(query)}"
        f"&num=10"
    )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GeoSearch/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for i, item in enumerate(data.get("items", []), start=1):
            results.append(
                {
                    "rank": i,
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                }
            )
        return results

    except urllib.error.HTTPError as e:
        # Read the error body for a useful message
        try:
            body = json.loads(e.read().decode("utf-8"))
            msg = body.get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        print(f"[Google API] HTTP {e.code}: {msg}")
        return _fallback_google(query, msg)

    except Exception as e:
        print(f"[Google API] Error: {e}")
        return _fallback_google(query, str(e))


def bing(query: str) -> dict:
    """Return Bing search URL for the query."""
    return {
        "engine": "bing",
        "search_url": f"https://www.bing.com/search?q={quote_plus(query)}",
        "query": query,
    }
