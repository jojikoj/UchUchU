"""静的サイトジェネレータ。

data/*.json（収集結果）+ content/articles/*.md（手書き記事）を読み、
日英2言語の静的サイトを dist/ に生成する。外部通信・AI APIは一切なし。

出力構成:
    dist/index.html            日本語トップ
    dist/news/ launches/ papers/ articles/
    dist/articles/<slug>/
    dist/en/... 同じ構成の英語版
    dist/static/  sitemap.xml robots.txt 404.html .nojekyll

実行:
    python -m uchuchu.build
"""
from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import config, seo
from .i18n import t as _t


# --- データ読み込み -----------------------------------------------------
def _load_json(name: str) -> dict:
    path = config.DATA_DIR / name
    if not path.exists():
        return {"items": [], "generated_at": None}
    return json.loads(path.read_text(encoding="utf-8"))


# --- 日付整形 -----------------------------------------------------------
_EN_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def fmt_date(iso: str | None, lang: str, with_time: bool = False) -> str | None:
    dt = _parse_iso(iso)
    if dt is None:
        return None
    if lang == "ja":
        base = f"{dt.year}年{dt.month}月{dt.day}日"
        if with_time:
            base += f" {dt.hour:02d}:{dt.minute:02d} UTC"
        return base
    base = f"{_EN_MONTHS[dt.month]} {dt.day}, {dt.year}"
    if with_time:
        base += f" {dt.hour:02d}:{dt.minute:02d} UTC"
    return base


def countdown_label(iso: str | None, now: datetime, lang: str) -> str | None:
    dt = _parse_iso(iso)
    if dt is None:
        return None
    delta = dt - now
    secs = int(delta.total_seconds())
    if secs <= 0:
        return "T-0" if lang == "en" else "まもなく"
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    if lang == "ja":
        if days > 0:
            return f"T-{days}日 {hours}時間"
        if hours > 0:
            return f"T-{hours}時間 {mins}分"
        return f"T-{mins}分"
    if days > 0:
        return f"T-{days}d {hours}h"
    if hours > 0:
        return f"T-{hours}h {mins}m"
    return f"T-{mins}m"


_STATUS_CLASS = {
    "go": "go", "success": "success", "tbd": "tbd", "tbc": "tbd",
    "hold": "hold", "failure": "hold", "partial failure": "hold",
    "in flight": "go",
}


# --- データ整形 ---------------------------------------------------------
def prepare_news(raw: list[dict], lang: str) -> list[dict]:
    """その言語サイトに載せるニュースを選び、表示用に整形する。

    ja: 全ソース。英語ソースは日本語訳（title_ja/summary_ja）があればそれを使う。
    en: 英語ソースのみ。日→英の機械翻訳は品質が低く公開に耐えないため、
        日本語ソースは英語サイトには載せない。
    """
    out = []
    for it in raw:
        if lang == "en" and it.get("lang") != "en":
            continue
        it = dict(it)
        it["published_display"] = fmt_date(it.get("published"), lang)
        # 自動翻訳で表示しているかどうか（UIバッジ用）
        it["is_translated"] = bool(
            it.get("lang") != lang and it.get(f"title_{lang}")
        )
        out.append(it)
    return out


def prepare_launches(raw: list[dict], lang: str, now: datetime) -> list[dict]:
    out = []
    for it in raw:
        it = dict(it)
        it["net_display"] = fmt_date(it.get("net"), lang, with_time=True)
        it["countdown"] = countdown_label(it.get("net"), now, lang)
        st = (it.get("status_name") or it.get("status") or "").lower()
        it["status_class"] = _STATUS_CLASS.get(st, "tbd")
        out.append(it)
    return out


def prepare_papers(raw: list[dict], lang: str) -> list[dict]:
    out = []
    for it in raw:
        it = dict(it)
        it["published_display"] = fmt_date(it.get("published"), lang)
        out.append(it)
    return out


# --- 記事(Markdown) ----------------------------------------------------
_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, m.group(2)


def load_articles(lang: str) -> list[dict]:
    """content/articles/<slug>.<lang>.md を読み込む。"""
    if not config.ARTICLES_DIR.exists():
        return []
    md = markdown.Markdown(extensions=["extra", "toc", "sane_lists"])
    articles = []
    for path in sorted(config.ARTICLES_DIR.glob(f"*.{lang}.md")):
        slug = path.name[: -len(f".{lang}.md")]
        meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
        md.reset()
        html = md.convert(body)
        articles.append({
            "slug": slug,
            "title": meta.get("title", slug),
            "excerpt": meta.get("excerpt", ""),
            "tag": meta.get("tag", ""),
            "author": meta.get("author", ""),
            "hero": meta.get("hero", ""),
            "date": meta.get("date", ""),
            "date_display": fmt_date(meta.get("date"), lang) if meta.get("date") else "",
            "order": int(meta.get("order", "100") or "100"),
            "html": html,
        })
    articles.sort(key=lambda a: (a["order"], a["date"]), reverse=False)
    return articles


# --- レンダリング -------------------------------------------------------
class Builder:
    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(config.TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True, lstrip_blocks=True,
        )
        self.now = datetime.now(timezone.utc)
        self.build_time = self.now.strftime("%Y-%m-%d %H:%M UTC")
        self.year = self.now.year
        self.base_url = os.environ.get("SITE_BASE_URL", config.SITE_BASE_URL).rstrip("/")
        self.news_raw = _load_json("news.json").get("items", [])
        self.launches_raw = _load_json("launches.json").get("items", [])
        self.papers_raw = _load_json("papers.json").get("items", [])

    # 相対パス prefix（dist直下=ルート、ページ深さに応じて ../ を積む）
    @staticmethod
    def _rel(depth: int) -> str:
        return "../" * depth if depth else ""

    def _lang_root(self, lang: str) -> str:
        """その言語のルート出力ディレクトリ（ja=dist, en=dist/en）。"""
        return config.DIST_DIR if lang == config.DEFAULT_LANG else config.DIST_DIR / lang

    def _url_for(self, lang: str, path: str) -> str:
        """絶対URL。path は 'news/' など（末尾スラッシュ）。"""
        prefix = "" if lang == config.DEFAULT_LANG else f"{lang}/"
        return f"{self.base_url}/{prefix}{path}"

    def _alternates(self, path: str) -> dict:
        return {l: self._url_for(l, path) for l in config.LANGS}

    def _ctx(self, lang: str, *, depth: int, active: str, path: str,
             page_description: str = "") -> dict:
        rel = self._rel(depth)  # 言語ルート基準（ナビ用）
        # アセット(css/js/img)はサイトルート(dist/)基準。en配下は1階層深いので補正。
        asset = rel + ("../" if lang != config.DEFAULT_LANG else "")
        return {
            "lang": lang,
            "t": lambda k: _t(k, lang),
            "site_name": config.SITE_NAME,
            "site_tagline": config.SITE_TAGLINE[lang],
            "site_description": config.SITE_DESCRIPTION[lang],
            "page_description": page_description,
            "rel": rel,
            "asset": asset,
            "home_url": rel or "./",
            "active": active,
            "year": self.year,
            "build_time": self.build_time,
            "canonical": self._url_for(lang, path),
            "site_base_url": self.base_url,
            "og_type": "article" if path.startswith("articles/") and path != "articles/" else "website",
            "alternates": self._alternates(path),
            # フィルタに出すソース。英語サイトには英語ソースのみ
            # （日本語ソースの記事は英語サイトに載せないため）。
            "news_sources": [
                s for s in config.NEWS_SOURCES
                if lang != "en" or s["lang"] == "en"
            ],
        }

    def _write(self, lang: str, path: str, html: str) -> None:
        out_dir = self._lang_root(lang) / path
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html, encoding="utf-8")

    def _write_root(self, lang: str, html: str) -> None:
        out_dir = self._lang_root(lang)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html, encoding="utf-8")

    def build_lang(self, lang: str) -> None:
        news = prepare_news(self.news_raw, lang)
        launches = prepare_launches(self.launches_raw, lang, self.now)
        papers = prepare_papers(self.papers_raw, lang)
        articles = load_articles(lang)
        home_label = _t("nav.home", lang)

        # トップ（depth: ja=0, en=1 だが rel は言語ルート基準なので 0）
        ctx = self._ctx(lang, depth=0, active="home", path="")
        ctx.update(news=news, launches=launches, papers=papers, articles=articles)
        ctx["jsonld"] = seo.build_jsonld(
            self.base_url, lang, "home",
            trail=[(home_label, self._url_for(lang, ""))])
        self._write_root(lang, self.env.get_template("home.html").render(**ctx))

        # 一覧ページ（言語ルートから1階層 → rel="../"）
        pages = [
            ("news/", "news.html", "news", {"news": news}),
            ("launches/", "launches.html", "launches", {"launches": launches}),
            ("papers/", "papers.html", "papers", {"papers": papers}),
            ("articles/", "articles.html", "articles", {"articles": articles}),
        ]
        for path, tpl, active, extra in pages:
            ctx = self._ctx(lang, depth=1, active=active, path=path)
            ctx.update(extra)
            ctx["jsonld"] = seo.build_jsonld(
                self.base_url, lang, active,
                trail=[(home_label, self._url_for(lang, "")),
                       (_t(f"nav.{active}", lang), self._url_for(lang, path))],
                news=news, launches=launches, papers=papers, articles=articles)
            self._write(lang, path, self.env.get_template(tpl).render(**ctx))

        # 記事詳細（articles/<slug>/ → depth 2）
        for a in articles:
            path = f"articles/{a['slug']}/"
            page_url = self._url_for(lang, path)
            ctx = self._ctx(lang, depth=2, active="articles", path=path,
                            page_description=a.get("excerpt", ""))
            ctx["article"] = a
            ctx["jsonld"] = seo.build_jsonld(
                self.base_url, lang, "article", article=a, page_url=page_url,
                trail=[(home_label, self._url_for(lang, "")),
                       (_t("nav.articles", lang), self._url_for(lang, "articles/")),
                       (a["title"], page_url)])
            html = self.env.get_template("article.html").render(**ctx)
            self._write(lang, f"articles/{a['slug']}", html)

        # RSSフィード
        feed = seo.build_feed(self.base_url, lang, articles, news, self.now)
        feed_dir = self._lang_root(lang)
        feed_dir.mkdir(parents=True, exist_ok=True)
        (feed_dir / "feed.xml").write_text(feed, encoding="utf-8")

        print(f"  [{lang}] home + {len(pages)} lists + {len(articles)} articles + feed.xml")

    # --- 付随ファイル ---
    def write_extras(self) -> None:
        # 静的アセット
        dest = config.DIST_DIR / "static"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(config.STATIC_DIR, dest)

        # .nojekyll（GitHub Pagesで _ 始まりを配信させる）
        (config.DIST_DIR / ".nojekyll").write_text("", encoding="utf-8")

        # CNAME（独自ドメイン）。サイトのルートに置く必要がある。
        if config.SITE_DOMAIN:
            (config.DIST_DIR / "CNAME").write_text(
                config.SITE_DOMAIN + "\n", encoding="utf-8")

        # robots.txt（検索エンジン＋AIクローラを明示許可）
        (config.DIST_DIR / "robots.txt").write_text(
            seo.build_robots(self.base_url), encoding="utf-8")

        # sitemap.xml（lastmod + hreflang相互リンク）
        paths = ["", "news/", "launches/", "papers/", "articles/"]
        articles_ja = load_articles(config.DEFAULT_LANG)
        for a in articles_ja:
            paths.append(f"articles/{a['slug']}/")
        (config.DIST_DIR / "sitemap.xml").write_text(
            seo.build_sitemap(self.base_url, paths, self.now), encoding="utf-8")

        # llms.txt（AI検索にサイト構造を伝える）
        articles_en = load_articles("en")
        (config.DIST_DIR / "llms.txt").write_text(
            seo.build_llms_txt(self.base_url, articles_ja, articles_en),
            encoding="utf-8")

        # 404
        ctx = self._ctx(config.DEFAULT_LANG, depth=0, active="", path="404")
        four04 = self.env.from_string(_FOUR04_TPL).render(**ctx)
        (config.DIST_DIR / "404.html").write_text(four04, encoding="utf-8")
        extras = "static/, .nojekyll, robots.txt, sitemap.xml, llms.txt, 404.html"
        if config.SITE_DOMAIN:
            extras += f", CNAME({config.SITE_DOMAIN})"
        print(f"  extras: {extras}")

    def run(self) -> None:
        print(f"=== UchUchU build @ {self.build_time} ===")
        print(f"  data: news={len(self.news_raw)} launches={len(self.launches_raw)} "
              f"papers={len(self.papers_raw)}")
        # dist をクリーン
        if config.DIST_DIR.exists():
            shutil.rmtree(config.DIST_DIR)
        config.DIST_DIR.mkdir(parents=True)
        for lang in config.LANGS:
            self.build_lang(lang)
        self.write_extras()
        print(f"=== done → {config.DIST_DIR} ===")


_FOUR04_TPL = """{% extends "base.html" %}
{% block title %}404{% endblock %}
{% block content %}
<section class="section" style="text-align:center;padding:12vh 0">
  <div class="wrap">
    <h1 style="font-size:clamp(3rem,12vw,7rem);margin:0">404</h1>
    <p class="page-sub">Lost in space. / 宇宙で迷子になりました。</p>
    <a class="btn btn-primary" href="{{ home_url or './' }}">Home</a>
  </div>
</section>
{% endblock %}"""


def main() -> int:
    Builder().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
