"""各データソースからの取得ロジック。

すべて無料の公開API/RSS。個別ソースの失敗は例外を握りつぶさず
呼び出し側へ返し、orchestrator がフェイルソフト処理する。
戻り値は正規化済みの dict。
"""
from __future__ import annotations

import html
import re
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

from .. import config


def _get(url: str, verify: str | bool = True) -> requests.Response:
    """共通のHTTP取得。

    verify に PEM を渡すと、そのファイルだけを信頼して検証する。
    中間証明書を正しく送らないサーバ（官公需情報ポータル）向け。
    検証を切るのではなく、正しい鎖を与えて通す。
    """
    r = requests.get(
        url, timeout=config.HTTP_TIMEOUT, verify=verify,
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


# --- 話題フィルタ -------------------------------------------------------
# 宇宙以外も配信する総合メディア向け。宇宙関連語を含む記事だけを採用する。
_SPACE_TERMS = [
    # 英語
    "space", "rocket", "launch", "orbit", "orbital", "satellite", "spacecraft",
    "astronaut", "cosmonaut", "nasa", "esa", "jaxa", "spacex", "blue origin",
    "rocket lab", "starship", "falcon 9", "moon", "lunar", "mars", "martian",
    "asteroid", "comet", "planet", "exoplanet", "galaxy", "telescope", "iss",
    "space station", "solar system", "jupiter", "saturn", "venus", "mercury",
    "neptune", "uranus", "pluto", "meteor", "eclipse", "cosmic", "astronomy",
    "astrophysic", "interstellar", "spaceflight", "payload", "booster",
    "artemis", "hubble", "webb", "voyager", "starlink", "deep space",
    # 日本語
    "宇宙", "ロケット", "打ち上げ", "衛星", "探査機", "宇宙飛行士", "軌道",
    "月面", "火星", "小惑星", "彗星", "銀河", "望遠鏡", "天文", "惑星",
    "国際宇宙ステーション", "スペースX", "スペースエックス", "はやぶさ",
    "太陽系", "木星", "土星", "金星", "天体", "星雲", "ブラックホール",
]


def is_space_related(item: dict) -> bool:
    """記事が宇宙関連かどうかを判定する（総合メディア向けの絞り込み）。"""
    blob = f"{item.get('title', '')} {item.get('summary', '')}".lower()
    return any(term in blob for term in _SPACE_TERMS)


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
    """Spaceflight News API v4。offset でページングして多数取得する。"""
    per_page = source.get("per_page", 50)
    pages = source.get("pages", 1)
    base = source["url"].rstrip("?&")
    items = []
    for page in range(pages):
        url = f"{base}?limit={per_page}&offset={page * per_page}"
        data = None
        # 一時的な失敗（レート制限など）は間を置いて再試行する
        for attempt in range(3):
            try:
                data = _get(url).json()
                break
            except Exception as e:
                if attempt == 2:
                    print(f"    [sfn] page{page} 取得失敗: {type(e).__name__}: {e}",
                          file=sys.stderr)
                else:
                    time.sleep(2 * (attempt + 1))
        if data is None:
            break  # 取得済み分は活かす
        results = data.get("results", [])
        if not results:
            break
        for a in results:
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
        if not data.get("next"):
            break
    return items


FETCHERS = {"rss": fetch_rss, "spaceflightnews": fetch_spaceflightnews}


def fetch_news_source(source: dict) -> list[dict]:
    fetcher = FETCHERS.get(source["type"], fetch_rss)
    items = fetcher(source)
    # 総合メディアは宇宙関連記事だけに絞る
    if source.get("topic_filter"):
        items = [it for it in items if is_space_related(it)]
    return items


# --- 打ち上げ -----------------------------------------------------------
def fetch_launches() -> list[dict]:
    """Launch Library 2 の打ち上げ（予定＋実績）。言語非依存の生データを返す。"""
    results = []
    for url, upcoming in ((config.LAUNCH_UPCOMING_URL, True),
                          (config.LAUNCH_PREVIOUS_URL, False)):
        try:
            data = _get(url).json()
        except Exception:
            continue  # 片方が落ちてももう片方は活かす
        for r in data.get("results", []):
            r["_upcoming"] = upcoming
            results.append(r)

    launches = []
    for l in results:
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
            # 打ち上げウィンドウの終了時刻。構造化データの endDate に使う。
            "window_end": l.get("window_end"),
            "status": (l.get("status") or {}).get("abbrev") or (l.get("status") or {}).get("name"),
            "status_name": (l.get("status") or {}).get("name"),
            "provider": provider.get("name"),
            "provider_country": provider.get("country_code"),
            # 運営者の公式サイト。無ければ Wikipedia（どちらも API 提供の実データ）
            "provider_url": provider.get("info_url") or provider.get("wiki_url"),
            "rocket": rocket.get("full_name") or rocket.get("name"),
            "pad": pad.get("name"),
            "pad_lat": pad.get("latitude"),
            "pad_lon": pad.get("longitude"),
            "location": location.get("name"),
            "country": location.get("country_code"),
            "mission": mission.get("name"),
            "mission_type": mission.get("type"),
            "mission_description": clean_text(mission.get("description", ""), limit=400),
            "image": image,
            "webcast": (l.get("vidURLs") or [{}])[0].get("url") if l.get("vidURLs") else None,
            "upcoming": l.get("_upcoming", True),
        })
    # 予定を先に、実績は新しい順で後ろに
    launches.sort(key=lambda x: (not x["upcoming"],
                                 x["net"] or "" if x["upcoming"] else ""))
    upcoming = [l for l in launches if l["upcoming"]]
    past = sorted([l for l in launches if not l["upcoming"]],
                  key=lambda x: x["net"] or "", reverse=True)
    return upcoming + past


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


# --- 調達情報 -----------------------------------------------------------
def _external_url(raw: str | None) -> str:
    """公告の外部リンク。

    調達APIは ExternalDocumentURI を相対パスで返すことがある
    （実例: "search2/geps2/2021/04/2021...")。そのまま出すと自サイトの
    内部リンクとして解釈され、リンク検査が落ちて公開が止まる（2026-08-22）。
    基底URLは公告ごとに違って復元できないので、絶対URLのものだけ載せる。
    """
    u = (raw or "").strip()
    return u if u.startswith(("http://", "https://")) else ""


def fetch_procurement() -> list[dict]:
    """官公需情報ポータルサイトの公告から、宇宙分野の案件を集める。

    参入したい製造業には「どこが何を発注しているか」、サプライヤーを
    探す宇宙ベンチャーには「業界が何を外に出しているか」が分かる。
    集約ニュースと違い、この一覧は他所に存在しない。

    XMLはUTF-8固定・1クエリ最大100件。取りこぼしを減らすため複数語で引く。
    """
    import urllib.parse
    import xml.etree.ElementTree as ET

    seen: dict[str, dict] = {}
    for q in config.PROCUREMENT_QUERIES:
        url = (f"{config.PROCUREMENT_API}?Query={urllib.parse.quote(q)}"
               f"&Count=100&CFT=1")
        try:
            resp = _get(url, verify=str(config.KKJ_CA_BUNDLE))
            root = ET.fromstring(resp.content)
        except Exception as e:
            # 1語落ちても他の語で拾えるので、ここでは止めない
            print(f"  FAIL procurement[{q}] {type(e).__name__}: {e}", file=sys.stderr)
            continue

        for r in root.findall(".//SearchResult"):
            key = (r.findtext("Key") or "").strip()
            name = (r.findtext("ProjectName") or "").strip()
            org = (r.findtext("OrganizationName") or "").strip()
            if not key or not name:
                continue
            # 他省庁の無関係な工事を弾く。宇宙分野の機関からの発注は
            # 案件名に語が無くても残す（「〜の購入」等が多いため）。
            # 判定に概要は使わない（定型文の語で誤ヒットするため）。
            if not (any(o in org for o in config.PROCUREMENT_ORGS)
                    or any(k in name for k in config.PROCUREMENT_KEYWORDS)):
                continue
            seen[key] = {
                "id": key,
                "name": name,
                "org": org,
                "url": _external_url(r.findtext("ExternalDocumentURI")),
                "issued": (r.findtext("CftIssueDate") or "").strip(),
                "prefecture": (r.findtext("PrefectureName") or "").strip(),
                "city": (r.findtext("CityName") or "").strip(),
                "description": clean_text(r.findtext("ProjectDescription") or "", limit=300),
                "file_type": (r.findtext("FileType") or "").strip(),
                "is_jaxa": "宇宙航空研究開発機構" in org,
            }
        time.sleep(1)   # 公共APIなので間隔を空ける

    items = list(seen.values())
    items.sort(key=lambda x: x.get("issued") or "", reverse=True)
    return items
