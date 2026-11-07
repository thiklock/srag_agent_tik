"""News tool. Google News rss, filtered by publisher domain and cleaned up."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from srag.guardrails import domain_allowed, sanitize_news_text

RSS_URL = "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"


class NewsItem(BaseModel):
    title: str
    source: str
    source_url: str
    published: str


def parse_rss(xml_text: str, limit: int = 5) -> list[NewsItem]:
    """Keep only allowlisted publishers and titles that pass the sanitiser."""
    items: list[NewsItem] = []
    for node in ET.fromstring(xml_text).iter("item"):
        source = node.find("source")
        source_url = source.get("url", "") if source is not None else ""
        if not domain_allowed(source_url):
            continue
        publisher = (source.text or "") if source is not None else ""
        title = sanitize_news_text(node.findtext("title") or "")
        if title is None:
            continue
        if publisher and title.endswith(f" - {publisher}"):
            title = title[: -len(publisher) - 3]  # google appends " - Publisher" to titles
        items.append(
            NewsItem(
                title=title,
                source=publisher,
                source_url=source_url,
                published=node.findtext("pubDate") or "",
            )
        )
        if len(items) >= limit:
            break
    return items


DEFAULT_QUERY = "SRAG síndrome respiratória aguda grave"


def search_news(query: str = DEFAULT_QUERY, limit: int = 5) -> list[NewsItem]:
    """Fetch the latest news. Network errors bubble up, the caller handles them."""
    resp = httpx.get(RSS_URL.format(q=quote(query)), timeout=15, follow_redirects=True)
    resp.raise_for_status()
    return parse_rss(resp.text, limit)
