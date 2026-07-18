"""各データソースからの取得ロジック。

すべて無料の公開API/RSS。個別ソースの失敗は例外を握りつぶさず
呼び出し側へ返し、orchestrator がフェイルソフト処理する。
戻り値は正規化済みの dict。
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

from .. import config


def _get(url: str) -> requests.Response:
    r = requests.get(
        url, timeout=config.HTTP_TIMEOUT,
        headers={"User-Agent": config.USER_AGENT, "Accept": "application/json, text/xml, */*"},
    )
    r.raise_for_status()
    return r


_TAG_RE = re.compile(r"<[^>]+>")


def clean_text(raw: str, limit: int = 320) -> str:
    """HTMLタグ・エンティティを除去して要約用の平文にする。"""
    if not raw:
        return ""
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_feed_date(entry) -> str | None:
    for key in ("published", "updated", "created"):
        val = entry.get(key)
        if not val:
            continue
        try:
            return _iso(parsedate_to_datetime(val))
        except (TypeError, ValueError):
            pass
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            try:
                return _iso(datetime(*st[:6], tzinfo=timezone.utc))
            except (TypeError, ValueError):
                pass
    return None


# --- ニュース -----------------------------------------------------------
def fetch_rss(source: dict) -> list[dict]:
    """汎用RSS/Atom取得。"""
    resp = _get(source["url"])
    feed = feedparser.parse(resp.content)
    items = []
    for e in feed.entries:
        summary = clean_text(e.get("summary") or e.get("description") or "")
        img = None
        # メディアサムネイルがあれば拾う
        if e.get("media_thumbnail"):
            img = e["media_thumbnail"][0].get("url")
        elif e.get("media_content"):
            img = e["media_content"][0].get("url")
        elif e.get("links"):
            for lk in e["links"]:
                if lk.get("type", "").startswith("image"):
                    img = lk.get("href")
                    break
        items.append({
            "title": clean_text(e.get("title", ""), limit=200),
            "url": e.get("link", ""),
            "summary": summary,
            "image": img,
            "published": _parse_feed_date(e),
            "source": source["name"],
            "source_id": source["id"],
            "lang": source["lang"],
        })
    return items


def fetch_spaceflightnews(source: dict) -> list[dict]:
    """Spaceflight News API v4。"""
    resp = _get(source["url"])
    data = resp.json()
    items = []
    for a in data.get("results", []):
        items.append({
            "title": clean_text(a.get("title", ""), limit=200),
            "url": a.get("url", ""),
            "summary": clean_text(a.get("summary", "")),
            "image": a.get("image_url"),
            "published": a.get("published_at"),
            "source": a.get("news_site") or source["name"],
            "source_id": source["id"],
            "lang": source["lang"],
        })
    return items


FETCHERS = {"rss": fetch_rss, "spaceflightnews": fetch_spaceflightnews}


def fetch_news_source(source: dict) -> list[dict]:
    fetcher = FETCHERS.get(source["type"], fetch_rss)
    return fetcher(source)


# --- 打ち上げ -----------------------------------------------------------
def fetch_launches() -> list[dict]:
    """Launch Library 2 の直近打ち上げ。言語非依存の生データを返す。"""
    resp = _get(config.LAUNCH_UPCOMING_URL)
    data = resp.json()
    launches = []
    for l in data.get("results", []):
        provider = (l.get("launch_service_provider") or {})
        pad = (l.get("pad") or {})
        location = (pad.get("location") or {})
        rocket = ((l.get("rocket") or {}).get("configuration") or {})
        mission = (l.get("mission") or {})
        image = l.get("image")
        if isinstance(image, dict):  # 新APIは dict の場合あり
            image = image.get("image_url") or image.get("thumbnail_url")
        launches.append({
            "id": l.get("id"),
            "name": l.get("name", ""),
            "net": l.get("net"),  # ISO打ち上げ予定時刻(UTC)
            "status": (l.get("status") or {}).get("abbrev") or (l.get("status") or {}).get("name"),
            "status_name": (l.get("status") or {}).get("name"),
            "provider": provider.get("name"),
            "provider_country": provider.get("country_code"),
            "rocket": rocket.get("full_name") or rocket.get("name"),
            "pad": pad.get("name"),
            "location": location.get("name"),
            "country": location.get("country_code"),
            "mission": mission.get("name"),
            "mission_type": mission.get("type"),
            "mission_description": clean_text(mission.get("description", ""), limit=400),
            "image": image,
            "webcast": (l.get("vidURLs") or [{}])[0].get("url") if l.get("vidURLs") else None,
        })
    return launches


# --- 論文 ---------------------------------------------------------------
def fetch_papers() -> list[dict]:
    """arXiv Atom API。宇宙開発関連の最新論文。"""
    resp = _get(config.ARXIV_QUERY_URL)
    feed = feedparser.parse(resp.content)
    papers = []
    for e in feed.entries:
        authors = [a.get("name") for a in e.get("authors", []) if a.get("name")]
        pdf = None
        for lk in e.get("links", []):
            if lk.get("title") == "pdf" or lk.get("type") == "application/pdf":
                pdf = lk.get("href")
        cats = [t.get("term") for t in e.get("tags", []) if t.get("term")]
        papers.append({
            "title": clean_text(e.get("title", ""), limit=250),
            "url": e.get("link", ""),
            "pdf": pdf,
            "summary": clean_text(e.get("summary", ""), limit=500),
            "authors": authors[:8],
            "categories": cats[:5],
            "published": _parse_feed_date(e),
        })
    return papers
