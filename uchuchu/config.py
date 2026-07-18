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
    "ja": "宇宙産業と、日本のものづくりをつなぐ。",
    "en": "Connecting Japan's manufacturing to the space industry.",
}
SITE_DESCRIPTION = {
    "ja": "日本の製造業が宇宙産業に参入・受注するための実務メディア。"
          "宇宙関連企業データベース、参入ガイド、調達情報、国内外のニュースを集約。",
    "en": "A practical media for manufacturers entering the space supply chain — "
          "company database, entry guides, procurement information, and global news.",
}
# 独自ドメイン。dist/CNAME に書き出され、GitHub Pages がこのドメインで配信する。
# 空文字にすると CNAME を出力しない（github.io のURLで公開）。
SITE_DOMAIN = "uchuchu.tech"

# 公開URL。デプロイ時に環境変数 SITE_BASE_URL で上書き可。
SITE_BASE_URL = "https://uchuchu.tech"

# --- 問い合わせ ---------------------------------------------------------
# 静的サイトのためサーバー側フォーム処理を持てない。
# mailto: で件名・本文を事前入力し、送信の手間を最小化する。
# 問い合わせはフォーム(GAS)で受けるため、サイト上にアドレスを出さない。
# 出すとスパム収集ボットに拾われ、迷惑メールが増える。
# 内部処理でも使わない（宛先はGAS側の NOTIFY_TO で管理する）。
CONTACT_EMAIL = ""

# Googleフォームの埋め込みURL。
# 設定すると問い合わせページにフォームを埋め込む。
# 空のあいだは、メーラーを開く自前フォームにフォールバックする。
# 取得方法: Googleフォーム編集画面 → 送信 → < > タブ → src="..." の中身
GOOGLE_FORM_URL = ""

# フォーム送信先。FormSubmit を使うと、アカウント登録もAPIキーも不要で
# 静的サイトのままフォーム送信を受け取れる。
# 初回送信時に CONTACT_EMAIL 宛へ有効化リンクが届き、一度クリックすれば以降は直接届く。
# 空にすると mailto フォールバック（訪問者のメーラーが開く）に戻る。
# コンテンツ部 共通GAS（全メディアの問い合わせを1つのデプロイで受ける）。
# 第三者サービスを経由せず、自社のGoogleアカウント内で完結する。
# 実体: claude_AIR/TOEcompany/コンテンツ部/共通/gas/受付.gs
FORM_ENDPOINT = "https://script.google.com/macros/s/AKfycbxqiGT4qGvWQf7Ip3IQyVLLSf8cfpBdl6ehGaIKucg8H0aMmywALYG24J0s58LneeBx/exec"
GOOGLE_FORM_HEIGHT = 1200
COMPANY_NAME = "株式会社TOE"
COMPANY_URL = "https://gtoe.info/"

LANGS = ["ja", "en"]
DEFAULT_LANG = "ja"

# --- データソース -------------------------------------------------------
# RSSニュースソース。lang でどちらの言語版に載せるかを決める。
# 個別ソースが落ちても収集全体は継続する（フェイルソフト）。
#
# "topic_filter": True を付けたソースは宇宙以外の記事も配信するため、
# 宇宙関連キーワードに一致した記事だけを採用する（sources.py の is_space_related）。
NEWS_SOURCES = [
    # --- 日本語ソース（一次情報・専門メディア）---
    # 日本語サイトが主軸のため、日本語オリジナル記事の比率を重視する。
    {"id": "jaxa", "name": "JAXA", "lang": "ja",
     "url": "https://www.jaxa.jp/rss/press_j.rdf", "type": "rss"},
    {"id": "naoj", "name": "国立天文台", "lang": "ja",
     "url": "https://www.nao.ac.jp/atom.xml", "type": "rss", "topic_filter": True},
    {"id": "sorae", "name": "sorae", "lang": "ja",
     "url": "https://sorae.info/feed", "type": "rss"},
    {"id": "spacemedia", "name": "Space Media", "lang": "ja",
     "url": "https://spacemedia.jp/feed", "type": "rss"},
    {"id": "sorabatake", "name": "宙畑", "lang": "ja",
     "url": "https://sorabatake.jp/feed/", "type": "rss"},
    {"id": "astroarts", "name": "アストロアーツ", "lang": "ja",
     "url": "https://www.astroarts.co.jp/article/feed.atom", "type": "rss"},
    # 総合メディア（宇宙関連記事のみ採用）
    {"id": "wired_jp", "name": "WIRED.jp", "lang": "ja",
     "url": "https://wired.jp/feed/rss", "type": "rss", "topic_filter": True},
    {"id": "gizmodo_jp", "name": "ギズモード・ジャパン", "lang": "ja",
     "url": "https://www.gizmodo.jp/index.xml", "type": "rss", "topic_filter": True},
    {"id": "karapaia", "name": "カラパイア", "lang": "ja",
     "url": "https://karapaia.com/index.rdf", "type": "rss", "topic_filter": True},

    # --- 英語ソース（公式機関）---
    {"id": "nasa", "name": "NASA", "lang": "en",
     "url": "https://www.nasa.gov/news-release/feed/", "type": "rss"},
    {"id": "esa", "name": "ESA", "lang": "en",
     "url": "https://www.esa.int/rssfeed/Our_Activities/Space_News", "type": "rss"},
    {"id": "esa_science", "name": "ESA Science", "lang": "en",
     "url": "https://www.esa.int/rssfeed/Our_Activities/Space_Science", "type": "rss"},

    # --- 英語ソース（専門メディア）---
    {"id": "spacenews", "name": "SpaceNews", "lang": "en",
     "url": "https://spacenews.com/feed/", "type": "rss"},
    {"id": "spaceflightnow", "name": "Spaceflight Now", "lang": "en",
     "url": "https://spaceflightnow.com/feed/", "type": "rss"},
    {"id": "nasaspaceflight", "name": "NASASpaceflight", "lang": "en",
     "url": "https://www.nasaspaceflight.com/feed/", "type": "rss"},
    {"id": "payloadspace", "name": "Payload", "lang": "en",
     "url": "https://payloadspace.com/feed/", "type": "rss"},
    {"id": "everydayastronaut", "name": "Everyday Astronaut", "lang": "en",
     "url": "https://everydayastronaut.com/feed/", "type": "rss"},
    {"id": "space_com", "name": "Space.com", "lang": "en",
     "url": "https://www.space.com/feeds/all", "type": "rss"},
    {"id": "universetoday", "name": "Universe Today", "lang": "en",
     "url": "https://www.universetoday.com/feed", "type": "rss"},
    {"id": "arstechnica", "name": "Ars Technica", "lang": "en",
     "url": "https://arstechnica.com/science/space/feed/", "type": "rss"},
    {"id": "phys_space", "name": "Phys.org", "lang": "en",
     "url": "https://phys.org/rss-feed/space-news/", "type": "rss"},
    {"id": "skyandtelescope", "name": "Sky & Telescope", "lang": "en",
     "url": "https://skyandtelescope.org/feed/", "type": "rss", "topic_filter": True},
    {"id": "teslarati", "name": "Teslarati", "lang": "en",
     "url": "https://www.teslarati.com/feed/", "type": "rss", "topic_filter": True},

    # --- 英語ソース（API・ページング対応）---
    {"id": "spaceflightnews", "name": "Spaceflight News", "lang": "en",
     "url": "https://api.spaceflightnewsapi.net/v4/articles/", "type": "spaceflightnews",
     "pages": 6, "per_page": 50},
]

# 打ち上げ（Launch Library 2 / The Space Devs）— 無料・言語非依存
# 予定と実績の両方を集め、打ち上げページの厚みを出す。
LAUNCH_UPCOMING_URL = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=100&mode=detailed"
LAUNCH_PREVIOUS_URL = "https://ll.thespacedevs.com/2.2.0/launch/previous/?limit=100&mode=detailed"

# 論文（arXiv）— 宇宙開発関連カテゴリを拡張
ARXIV_QUERY_URL = (
    "http://export.arxiv.org/api/query?"
    "search_query=cat:astro-ph.IM+OR+cat:astro-ph.EP+OR+cat:physics.space-ph"
    "+OR+cat:astro-ph.SR+OR+cat:astro-ph.GA+OR+cat:astro-ph.HE"
    "&sortBy=submittedDate&sortOrder=descending&max_results=250"
)

# 保持する最大件数（アーカイブ蓄積の上限）
NEWS_LIMIT = 600
PAPERS_LIMIT = 250
LAUNCHES_LIMIT = 200

# 一覧ページの1ページあたり表示件数
PAGE_SIZE = 30

# ネットワーク
HTTP_TIMEOUT = 25
USER_AGENT = "UchUchU/1.0 (+https://github.com/; space-news aggregator)"
