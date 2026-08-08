"""Reader-mode article extraction: httpx fetch + trafilatura.

The SSRF guard matters even for a personal tool: article URLs come from
external feeds, so we never let the backend be steered at internal hosts.
"""

import asyncio
import ipaddress
import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import httpx
import trafilatura

from arcturus_api.domain.market.errors import ArticleFetchError
from arcturus_api.domain.market.fundamentals import ArticleContent
from arcturus_api.domain.market.ports import ArticleReader

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT_SECONDS = 8.0
_MAX_BYTES = 3_000_000
_BLOCKED_HOSTS = {"localhost", "0.0.0.0", "metadata.google.internal"}

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def validate_public_http_url(url: str) -> None:
    """Raise ArticleFetchError unless the URL is public http(s)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ArticleFetchError(url, "unsupported scheme")
    host = parsed.hostname
    if not host:
        raise ArticleFetchError(url, "missing host")
    if host.lower() in _BLOCKED_HOSTS:
        raise ArticleFetchError(url, "blocked host")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return  # a DNS name; acceptable
    if not address.is_global:
        raise ArticleFetchError(url, "non-public address")


def extract_article(url: str, html: str) -> ArticleContent:
    """Pure extraction from fetched HTML (unit-testable)."""
    text = trafilatura.extract(html, include_comments=False, favor_precision=True)
    metadata: Any = trafilatura.extract_metadata(html)

    title = getattr(metadata, "title", None)
    site_name = getattr(metadata, "sitename", None)
    image_url = getattr(metadata, "image", None)
    raw_date = getattr(metadata, "date", None)
    published_at: datetime | None = None
    if isinstance(raw_date, str):
        try:
            published_at = datetime.fromisoformat(raw_date)
        except ValueError:
            published_at = None

    return ArticleContent(
        url=url,
        title=title if isinstance(title, str) else None,
        text=text,
        site_name=site_name if isinstance(site_name, str) else None,
        image_url=image_url if isinstance(image_url, str) else None,
        published_at=published_at,
    )


class TrafilaturaArticleReader(ArticleReader):
    name = "trafilatura"

    async def read(self, url: str) -> ArticleContent:
        validate_public_http_url(url)
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=_FETCH_TIMEOUT_SECONDS,
                headers={"User-Agent": _USER_AGENT},
            ) as client:
                response = await client.get(url)
        except httpx.HTTPError as exc:
            raise ArticleFetchError(url, f"fetch failed: {type(exc).__name__}") from exc

        if response.status_code >= 400:
            raise ArticleFetchError(url, f"HTTP {response.status_code}")
        if len(response.content) > _MAX_BYTES:
            raise ArticleFetchError(url, "response too large")

        # trafilatura is CPU-bound C-backed parsing; keep it off the event loop
        return await asyncio.to_thread(extract_article, str(response.url), response.text)
