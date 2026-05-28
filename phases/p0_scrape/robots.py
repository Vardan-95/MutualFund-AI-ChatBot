from __future__ import annotations

from functools import lru_cache
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx


@lru_cache(maxsize=8)
def _robot_parser(base_url: str, user_agent: str) -> RobotFileParser:
    parsed = urlparse(base_url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(robots_url, headers={"User-Agent": user_agent})
            if response.status_code == 200:
                rp.parse(response.text.splitlines())
            else:
                rp.parse([])
    except Exception:
        rp.parse([])
    return rp


def is_allowed(url: str, user_agent: str) -> bool:
    """Return True if robots.txt permits fetching this URL."""
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    rp = _robot_parser(base, user_agent)
    return rp.can_fetch(user_agent, url)
