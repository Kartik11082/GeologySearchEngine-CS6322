import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

from config import PER_DOMAIN_DELAY, REQUEST_TIMEOUT_CONNECT, REQUEST_TIMEOUT_READ, USER_AGENT
from utils import extract_domain


class RobotsManager:
    def __init__(
        self,
        session: requests.Session,
        user_agent: str = USER_AGENT,
        per_domain_delay: float = PER_DOMAIN_DELAY,
    ) -> None:
        self.session = session
        self.user_agent = user_agent
        self.per_domain_delay = per_domain_delay
        self._robot_parsers: dict[str, RobotFileParser | None] = {}
        self._last_request_ts: dict[str, float] = {}

    def _cache_key(self, url: str) -> str:
        parts = urlsplit(url)
        scheme = (parts.scheme or "http").lower()
        domain = (parts.netloc or "").lower()
        return f"{scheme}://{domain}"

    def _build_parser(self, robots_url: str) -> RobotFileParser | None:
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            response = self.session.get(
                robots_url,
                timeout=(REQUEST_TIMEOUT_CONNECT, REQUEST_TIMEOUT_READ),
                allow_redirects=True,
                headers={"User-Agent": self.user_agent},
            )
        except requests.RequestException:
            return None

        if response.status_code == 200 and response.text:
            parser.parse(response.text.splitlines())
        else:
            parser.parse([])
        return parser

    def _get_parser(self, url: str) -> RobotFileParser | None:
        key = self._cache_key(url)
        if key in self._robot_parsers:
            return self._robot_parsers[key]

        robots_url = f"{key}/robots.txt"
        parser = self._build_parser(robots_url)
        self._robot_parsers[key] = parser
        return parser

    def is_allowed(self, url: str) -> bool:
        parser = self._get_parser(url)
        if parser is None:
            return True

        try:
            allowed = parser.can_fetch(self.user_agent, url)
            if allowed:
                return True
            return parser.can_fetch("*", url)
        except Exception:
            return True

    def wait_if_needed(self, url: str) -> None:
        domain = extract_domain(url)
        if not domain:
            return
        now = time.monotonic()
        previous = self._last_request_ts.get(domain)
        if previous is not None:
            wait_time = self.per_domain_delay - (now - previous)
            if wait_time > 0:
                time.sleep(wait_time)
        self._last_request_ts[domain] = time.monotonic()
