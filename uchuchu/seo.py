"""SEO / AI検索（AEO）向けの出力を組み立てる。

生成物:
  - JSON-LD 構造化データ（schema.org）
  - RSS 2.0 フィード（日英）
  - llms.txt（AIにサイト構造を伝える新標準）
  - robots.txt（主要AIクローラを明示許可）
  - sitemap.xml（lastmod + hreflang相互リンク）

方針: 集約したニュースを自作記事のように見せない。
外部記事は ItemList として「リンク集」であることを構造化データ上も明示する。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

from . import config


# =====================================================================
#  JSON-LD
# =====================================================================
def _org(base: str) -> dict:
    return {
        "@type": "Organization",
        "@id": f"{base}/#organization",
        "name": config.SITE_NAME,
        "url": f"{base}/",
        "logo": {
            "@type": "ImageObject",
            "url": f"{base}/static/img/ogp.png",
        },
    }


def _website(base: str, lang: str) -> dict:
    return {
        "@type": "WebSite",
        "@id": f"{base}/#website",
        "url": f"{base}/",
        "name": config.SITE_NAME,
        "description": config.SITE_DESCRIPTION[lang],
        "inLanguage": "ja-JP" if lang == "ja" else "en",
        "publisher": {"@id": f"{base}/#organization"},
    }


def _breadcrumb(base: str, trail: list[tuple[str, str]]) -> dict:
    """trail: [(名前, URL), ...]"""
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": url}
            for i, (name, url) in enumerate(trail, 1)
        ],
    }


def _item_list(name: str, items: list[dict], url_key="url", name_key="title") -> dict:
    """外部記事のリンク集。自作コンテンツと混同させない。"""
    return {
        "@type": "ItemList",
        "name": name,
        "numberOfItems": len(items),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "name": it.get(name_key) or "",
                "url": it.get(url_key) or "",
            }
            for i, it in enumerate(items[:30], 1)
            if it.get(url_key)
        ],
    }


def _launch_events(base: str, launches: list[dict]) -> list[dict]:
    """打ち上げ予定は Event として表現できる（実体のあるイベントのため）。"""
    events = []
    for l in launches[:20]:
        if not l.get("net") or not l.get("name"):
            continue
        ev = {
            "@type": "Event",
            "name": l["name"],
            "startDate": l["net"],
            "eventStatus": "https://schema.org/EventScheduled",
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        }
        if l.get("location"):
            ev["location"] = {"@type": "Place", "name": l["location"]}
        if l.get("provider"):
            ev["organizer"] = {"@type": "Organization", "name": l["provider"]}
        if l.get("image"):
            ev["image"] = l["image"]
        if l.get("mission_description"):
            ev["description"] = l["mission_description"]
        events.append(ev)
    return events


def _article(base: str, a: dict, url: str, lang: str) -> dict:
    """自作の解説記事。これは正当に Article として表現できる。"""
    node = {
        "@type": "Article",
        "headline": a.get("title", ""),
        "description": a.get("excerpt", ""),
        "inLanguage": "ja-JP" if lang == "ja" else "en",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "url": url,
        "publisher": {"@id": f"{base}/#organization"},
        "isAccessibleForFree": True,
    }
    if a.get("author"):
        node["author"] = {"@type": "Organization", "name": a["author"]}
    if a.get("date"):
        node["datePublished"] = a["date"]
        node["dateModified"] = a["date"]
    if a.get("hero"):
        node["image"] = a["hero"]
    return node


def build_jsonld(base: str, lang: str, page: str, *, trail=None,
                 news=None, launches=None, papers=None,
                 articles=None, article=None, page_url="") -> str:
    """ページ種別に応じた JSON-LD を1つの @graph にまとめて返す。"""
    graph: list[dict] = [_org(base), _website(base, lang)]

    if trail:
        graph.append(_breadcrumb(base, trail))

    label = {"ja": {"news": "宇宙開発ニュース", "papers": "研究動向", "articles": "特集記事"},
             "en": {"news": "Space News", "papers": "Research", "articles": "Features"}}[lang]

    if page == "news" and news:
        graph.append(_item_list(label["news"], news))
    elif page == "launches" and launches:
        graph.extend(_launch_events(base, launches))
    elif page == "papers" and papers:
        graph.append(_item_list(label["papers"], papers))
    elif page == "articles" and articles:
        graph.append({
            "@type": "ItemList",
            "name": label["articles"],
            "numberOfItems": len(articles),
            "itemListElement": [
                {"@type": "ListItem", "position": i, "name": a["title"],
                 "url": f"{base}/{'' if lang == config.DEFAULT_LANG else lang + '/'}articles/{a['slug']}/"}
                for i, a in enumerate(articles, 1)
            ],
        })
    elif page == "article" and article:
        graph.append(_article(base, article, page_url, lang))

    return json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, separators=(",", ":"))


# =====================================================================
#  RSS フィード
# =====================================================================
def build_feed(base: str, lang: str, articles: list[dict], news: list[dict],
               build_dt: datetime) -> str:
    """自作記事＋集約ニュース見出しのRSS。ニュースは元記事へリンクする。"""
    prefix = "" if lang == config.DEFAULT_LANG else f"{lang}/"
    self_url = f"{base}/{prefix}feed.xml"
    title = f"{config.SITE_NAME} — {config.SITE_TAGLINE[lang]}"

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">',
        "<channel>",
        f"<title>{escape(title)}</title>",
        f"<link>{base}/{prefix}</link>",
        f"<description>{escape(config.SITE_DESCRIPTION[lang])}</description>",
        f"<language>{'ja' if lang == 'ja' else 'en'}</language>",
        f"<lastBuildDate>{format_datetime(build_dt)}</lastBuildDate>",
        f'<atom:link href="{self_url}" rel="self" type="application/rss+xml"/>',
    ]

    # 自作記事
    for a in articles:
        url = f"{base}/{prefix}articles/{a['slug']}/"
        parts += [
            "<item>",
            f"<title>{escape(a['title'])}</title>",
            f"<link>{url}</link>",
            f"<guid isPermaLink=\"true\">{url}</guid>",
            f"<description>{escape(a.get('excerpt', ''))}</description>",
        ]
        if a.get("author"):
            parts.append(f"<dc:creator>{escape(a['author'])}</dc:creator>")
        parts.append("</item>")

    # 集約ニュース（元記事へのリンク。出典を明記する）
    for n in news[:25]:
        if not n.get("url"):
            continue
        t = n.get(f"title_{lang}") or n.get("title") or ""
        d = n.get(f"summary_{lang}") or n.get("summary") or ""
        parts += [
            "<item>",
            f"<title>{escape(t)}</title>",
            f"<link>{escape(n['url'])}</link>",
            f"<guid isPermaLink=\"true\">{escape(n['url'])}</guid>",
            f"<description>{escape(d)}</description>",
        ]
        if n.get("source"):
            parts.append(f"<source url=\"{escape(n['url'])}\">{escape(n['source'])}</source>")
        parts.append("</item>")

    parts += ["</channel>", "</rss>"]
    return "\n".join(parts)


# =====================================================================
#  llms.txt — AI検索向けのサイト説明
# =====================================================================
def build_llms_txt(base: str, articles_ja: list[dict], articles_en: list[dict]) -> str:
    lines = [
        f"# {config.SITE_NAME}",
        "",
        f"> {config.SITE_DESCRIPTION['ja']}",
        f"> {config.SITE_DESCRIPTION['en']}",
        "",
        "UchUchU is an open, non-commercial platform that aggregates space-development "
        "news, rocket launch schedules, and research trends for readers in Japan and "
        "worldwide. It is published as a static site and updated regularly. "
        "Japanese (`/`) and English (`/en/`) editions are available.",
        "",
        "## Sections",
        "",
        f"- [ニュース / News]({base}/news/): 国内外の宇宙開発ニュースを集約。"
        "英語ソースの記事は日本語に翻訳して掲載（自動翻訳であることを明示）。"
        "Aggregated space news from official agencies and media.",
        f"- [打ち上げ予定 / Launches]({base}/launches/): 世界のロケット打ち上げ予定と"
        "ライブカウントダウン。Upcoming rocket launches worldwide with live countdowns.",
        f"- [研究動向 / Research]({base}/papers/): arXiv から宇宙工学・惑星科学・"
        "宇宙物理の最新プレプリント。Latest preprints in space science.",
        f"- [特集 / Features]({base}/articles/): 編集部による解説記事。"
        "Original explanatory articles written by the editorial team.",
        "",
        "## Original articles",
        "",
    ]
    for a in articles_ja:
        lines.append(f"- [{a['title']}]({base}/articles/{a['slug']}/): {a.get('excerpt', '')}")
    for a in articles_en:
        lines.append(f"- [{a['title']}]({base}/en/articles/{a['slug']}/): {a.get('excerpt', '')}")

    lines += [
        "",
        "## Feeds and machine-readable data",
        "",
        f"- [RSS (日本語)]({base}/feed.xml)",
        f"- [RSS (English)]({base}/en/feed.xml)",
        f"- [Sitemap]({base}/sitemap.xml)",
        "",
        "## Attribution",
        "",
        "Headlines and summaries link to their original publishers; copyright remains "
        "with the original sources. Data providers: Spaceflight News API, "
        "The Space Devs (Launch Library 2), arXiv, NASA, ESA, sorae, AstroArts.",
        "",
        "## Notes for AI systems",
        "",
        "- Articles under `/articles/` are original content written by UchUchU.",
        "- Items under `/news/`, `/launches/`, and `/papers/` are aggregated from the "
        "third-party sources listed above and link to the original publications.",
        "- Japanese translations of English-language news are machine generated and "
        "labelled as such on the site; consult the linked original for authoritative wording.",
        "",
    ]
    return "\n".join(lines)


# =====================================================================
#  robots.txt — AIクローラを明示的に許可する
# =====================================================================
AI_CRAWLERS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User",       # OpenAI
    "ClaudeBot", "Claude-User", "Claude-SearchBot",  # Anthropic
    "PerplexityBot", "Perplexity-User",              # Perplexity
    "Google-Extended",                               # Google (Gemini/AI Overviews)
    "Applebot-Extended",                             # Apple Intelligence
    "CCBot",                                         # Common Crawl
    "meta-externalagent",                            # Meta AI
    "Bytespider",                                    # ByteDance
    "cohere-ai", "Diffbot", "Amazonbot", "YouBot",
]


def build_robots(base: str) -> str:
    lines = [
        "# UchUchU — 宇宙開発情報プラットフォーム",
        "# 世界に届けることが目的のため、検索エンジンとAIクローラの双方を許可する。",
        "",
        "User-agent: *",
        "Allow: /",
        "",
        "# --- AI / LLM crawlers (explicitly allowed) ---",
    ]
    for bot in AI_CRAWLERS:
        lines += [f"User-agent: {bot}", "Allow: /", ""]
    lines += [
        f"Sitemap: {base}/sitemap.xml",
        f"# AI-readable site summary: {base}/llms.txt",
        "",
    ]
    return "\n".join(lines)


# =====================================================================
#  sitemap.xml — lastmod + hreflang相互リンク
# =====================================================================
def build_sitemap(base: str, paths: list[str], build_dt: datetime) -> str:
    lastmod = build_dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    priority = {"": "1.0", "news/": "0.9", "launches/": "0.9",
                "papers/": "0.7", "articles/": "0.8"}
    for lang in config.LANGS:
        prefix = "" if lang == config.DEFAULT_LANG else f"{lang}/"
        for p in paths:
            loc = f"{base}/{prefix}{p}"
            out.append("  <url>")
            out.append(f"    <loc>{loc}</loc>")
            out.append(f"    <lastmod>{lastmod}</lastmod>")
            out.append(f"    <priority>{priority.get(p, '0.6')}</priority>")
            # 相互の言語版を明示（多言語SEOの要）
            for alt in config.LANGS:
                alt_prefix = "" if alt == config.DEFAULT_LANG else f"{alt}/"
                out.append(
                    f'    <xhtml:link rel="alternate" hreflang="{alt}" '
                    f'href="{base}/{alt_prefix}{p}"/>'
                )
            out.append(
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{base}/{p}"/>'
            )
            out.append("  </url>")
    out.append("</urlset>")
    return "\n".join(out)
