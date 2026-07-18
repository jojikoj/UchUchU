"""UI文言の日英辞書。テンプレートには t(key) 経由で渡す。"""
from __future__ import annotations

STRINGS = {
    "nav.home": {"ja": "ホーム", "en": "Home"},
    "nav.news": {"ja": "ニュース", "en": "News"},
    "nav.launches": {"ja": "打ち上げ", "en": "Launches"},
    "nav.papers": {"ja": "研究動向", "en": "Research"},
    "nav.articles": {"ja": "特集", "en": "Features"},

    "hero.cta_news": {"ja": "最新ニュースを見る", "en": "Latest news"},
    "hero.cta_launches": {"ja": "打ち上げ予定", "en": "Upcoming launches"},

    "home.latest_news": {"ja": "最新ニュース", "en": "Latest News"},
    "home.upcoming_launches": {"ja": "次の打ち上げ", "en": "Upcoming Launches"},
    "home.features": {"ja": "特集記事", "en": "Featured Articles"},
    "home.research": {"ja": "最新の研究動向", "en": "Latest Research"},
    "home.view_all": {"ja": "すべて見る", "en": "View all"},

    "news.title": {"ja": "宇宙開発ニュース", "en": "Space News"},
    "news.subtitle": {"ja": "国内外の公式発表とメディアを横断して集約。",
                      "en": "Aggregated from official and media sources worldwide."},
    "news.read_source": {"ja": "元記事を読む", "en": "Read source"},
    "news.filter_all": {"ja": "すべて", "en": "All"},

    "launches.title": {"ja": "ロケット打ち上げ予定", "en": "Rocket Launch Schedule"},
    "launches.subtitle": {"ja": "世界中の直近の打ち上げをリアルタイムデータで。",
                          "en": "Upcoming launches worldwide with live data."},
    "launches.provider": {"ja": "運用者", "en": "Provider"},
    "launches.rocket": {"ja": "ロケット", "en": "Rocket"},
    "launches.site": {"ja": "射場", "en": "Launch site"},
    "launches.mission": {"ja": "ミッション", "en": "Mission"},
    "launches.watch": {"ja": "中継を見る", "en": "Watch live"},
    "launches.status": {"ja": "ステータス", "en": "Status"},
    "launches.countdown": {"ja": "まで", "en": "to launch"},

    "papers.title": {"ja": "研究動向 (arXiv)", "en": "Research Trends (arXiv)"},
    "papers.subtitle": {"ja": "宇宙工学・惑星科学・宇宙物理の最新プレプリント。",
                        "en": "Latest preprints in space engineering and astrophysics."},
    "papers.authors": {"ja": "著者", "en": "Authors"},
    "papers.pdf": {"ja": "PDF", "en": "PDF"},
    "papers.abstract": {"ja": "概要", "en": "Abstract"},

    "articles.title": {"ja": "特集記事", "en": "Feature Articles"},
    "articles.subtitle": {"ja": "宇宙開発をわかりやすく掘り下げる読み物。",
                          "en": "In-depth reads that make space exploration clear."},
    "articles.read": {"ja": "続きを読む", "en": "Read more"},
    "articles.back": {"ja": "特集一覧へ戻る", "en": "Back to features"},

    "meta.machine_translated": {"ja": "自動翻訳", "en": "Machine translated"},
    "meta.mt_note": {
        "ja": "海外ソースの記事は、この場で自動翻訳して掲載しています（機械翻訳のため訳文が不正確な場合があります）。正確な内容は各記事の元記事をご確認ください。",
        "en": "Articles from non-English sources are machine translated. Please refer to the original article for accuracy.",
    },
    "meta.source": {"ja": "出典", "en": "Source"},
    "meta.updated": {"ja": "更新", "en": "Updated"},
    "meta.published": {"ja": "公開", "en": "Published"},
    "meta.no_data": {"ja": "データを取得できませんでした。次回更新をお待ちください。",
                     "en": "No data available. Please check back after the next update."},

    "footer.about": {"ja": "UchUchUについて", "en": "About UchUchU"},
    "footer.desc": {"ja": "宇宙開発の「いま」を国内外へ発信するオープンなプラットフォーム。運用中にAI APIを使わず、無料の公開データのみで動きます。",
                    "en": "An open platform broadcasting the present of space exploration to Japan and the world — running only on free public data, with no AI API cost."},
    "footer.sources": {"ja": "データ提供", "en": "Data sources"},
    "footer.built": {"ja": "静的サイト・自動更新", "en": "Static site · auto-updated"},
    "footer.lang": {"ja": "言語", "en": "Language"},
}


def t(key: str, lang: str) -> str:
    entry = STRINGS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("en") or key
