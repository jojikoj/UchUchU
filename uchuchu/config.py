"""UchUchU グローバル設定。

サイト全体のメタ情報・データソース・言語設定を一元管理する。
運用中に外部AI APIを一切叩かない設計（収集はすべて無料の公開API/RSS）。
"""
from __future__ import annotations

from pathlib import Path

# --- パス ---------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONTENT_DIR = ROOT / "content"
ARTICLES_DIR = CONTENT_DIR / "articles"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = ROOT / "static"
DIST_DIR = ROOT / "dist"

# --- サイト情報 ---------------------------------------------------------
SITE_NAME = "UchUchU"
SITE_TAGLINE = {
    "ja": "宇宙開発を、世界とつなぐ。",
    "en": "Connecting space exploration to the world.",
}
SITE_DESCRIPTION = {
    "ja": "国内外の宇宙開発ニュース・打ち上げ予定・研究動向を一か所に集約する発信プラットフォーム。",
    "en": "A platform aggregating global space-exploration news, launch schedules, and research trends in one place.",
}
# 独自ドメイン。dist/CNAME に書き出され、GitHub Pages がこのドメインで配信する。
# 空文字にすると CNAME を出力しない（github.io のURLで公開）。
SITE_DOMAIN = "uchuchu.tech"

# 公開URL。デプロイ時に環境変数 SITE_BASE_URL で上書き可。
SITE_BASE_URL = "https://uchuchu.tech"

LANGS = ["ja", "en"]
DEFAULT_LANG = "ja"

# --- データソース -------------------------------------------------------
# RSSニュースソース。lang でどちらの言語版に載せるかを決める。
# 個別ソースが落ちても収集全体は継続する（フェイルソフト）。
NEWS_SOURCES = [
    # 日本語ソース
    {"id": "sorae", "name": "sorae 宇宙へのポータルサイト", "lang": "ja",
     "url": "https://sorae.info/feed", "type": "rss"},
    {"id": "astroarts", "name": "アストロアーツ", "lang": "ja",
     "url": "https://www.astroarts.co.jp/article/feed.atom", "type": "rss"},
    # 英語ソース
    {"id": "nasa", "name": "NASA", "lang": "en",
     "url": "https://www.nasa.gov/news-release/feed/", "type": "rss"},
    {"id": "esa", "name": "ESA", "lang": "en",
     "url": "https://www.esa.int/rssfeed/Our_Activities/Space_News", "type": "rss"},
    {"id": "spaceflightnews", "name": "Spaceflight News", "lang": "en",
     "url": "https://api.spaceflightnewsapi.net/v4/articles/?limit=40", "type": "spaceflightnews"},
]

# 打ち上げ（Launch Library 2 / The Space Devs）— 無料・言語非依存
LAUNCH_UPCOMING_URL = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=30&mode=detailed"

# 論文（arXiv）— 宇宙開発関連カテゴリ
ARXIV_QUERY_URL = (
    "http://export.arxiv.org/api/query?"
    "search_query=cat:astro-ph.IM+OR+cat:astro-ph.EP+OR+cat:physics.space-ph"
    "&sortBy=submittedDate&sortOrder=descending&max_results=25"
)

# 一覧の表示件数
NEWS_LIMIT = 60
PAPERS_LIMIT = 25
LAUNCHES_LIMIT = 30

# ネットワーク
HTTP_TIMEOUT = 25
USER_AGENT = "UchUchU/1.0 (+https://github.com/; space-news aggregator)"
