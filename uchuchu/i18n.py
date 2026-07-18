"""UI文言の日英辞書。テンプレートには t(key) 経由で渡す。"""
from __future__ import annotations

STRINGS = {
    "side.by_tag": {"ja": "タグから探す", "en": "Browse by tag"},
    "side.search_ph": {"ja": "記事を検索", "en": "Search articles"},

    "brand.tagline": {"ja": "宇宙産業ポータル", "en": "Space Industry Portal"},

    "nav.home": {"ja": "ホーム", "en": "Home"},
    "nav.news": {"ja": "ニュース", "en": "News"},
    "nav.launches": {"ja": "打ち上げ", "en": "Launches"},
    "nav.papers": {"ja": "研究動向", "en": "Research"},
    "nav.articles": {"ja": "特集", "en": "Features"},

    "hero.cta_news": {"ja": "最新ニュースを見る", "en": "Latest news"},
    "hero.cta_launches": {"ja": "打ち上げ予定", "en": "Upcoming launches"},

    "home.popular_tags": {"ja": "話題のタグ", "en": "Popular tags"},

    "home.eyebrow": {"ja": "宇宙産業 × 日本のものづくり", "en": "SPACE INDUSTRY × JAPANESE MANUFACTURING"},
    "home.positioning": {
        "ja": "宇宙産業に関わる企業データベース、参入の実務ガイド、国内外のニュースを集約。自社の技術が宇宙でどう活きるかを探す製造業のための媒体です。",
        "en": "A company database, practical entry guides, and global news for manufacturers exploring how their technology fits the space industry."},
    "home.cta_db": {"ja": "企業データベースを見る", "en": "Browse the database"},
    "home.cta_guide": {"ja": "参入ガイドを読む", "en": "Read the entry guides"},
    "home.db_title": {"ja": "宇宙産業 企業データベース", "en": "Space Industry Company Database"},
    "home.db_lead": {
        "ja": "日本の宇宙産業に関わる企業を事業領域別に整理しています。取引先探索・競合把握にお使いください。掲載は無料です。",
        "en": "Japanese companies in the space industry, organised by business area. Listing is free."},
    "home.db_more": {"ja": "すべての企業を見る", "en": "View all companies"},
    "home.guide_title": {"ja": "宇宙産業 参入ガイド", "en": "Entry Guides"},
    "home.guide_lead": {
        "ja": "「うちの技術は宇宙で使えるのか」「何から始めればいいのか」に答える実務記事です。",
        "en": "Practical answers to \"can our technology be used in space\" and \"where do we start\"."},
    "home.cta_title": {"ja": "宇宙産業への参入・広告掲載のご相談", "en": "Talk to us"},
    "home.cta_body": {
        "ja": "自社技術が宇宙産業で活きるかのご相談、企業データベースへの掲載（無料）、広告掲載のご相談を承っています。",
        "en": "We welcome inquiries about entering the space industry, free database listings, and advertising."},

    "form.kind": {"ja": "ご用件", "en": "Inquiry type"},
    "form.company": {"ja": "貴社名", "en": "Company"},
    "form.name": {"ja": "ご担当者名", "en": "Your name"},
    "form.email": {"ja": "メールアドレス", "en": "Email"},
    "form.tel": {"ja": "電話番号（任意）", "en": "Phone (optional)"},
    "form.site": {"ja": "貴社サイトURL（任意）", "en": "Website (optional)"},
    "form.message": {"ja": "ご相談内容", "en": "Message"},
    "form.message_ph": {
        "ja": "例）金属加工を行っています。自社の技術が宇宙分野で活かせるか相談したい。",
        "en": "e.g. We do metal machining and want to know if our technology fits the space sector."},
    "form.submit": {"ja": "送信する", "en": "Send"},
    "form.sending": {"ja": "送信中…", "en": "Sending…"},
    "form.sent": {"ja": "送信しました。ありがとうございます。", "en": "Sent. Thank you."},
    "form.failed": {"ja": "送信に失敗しました。お手数ですがメールでご連絡ください。", "en": "Failed to send. Please email us instead."},
    "form.mail_opened": {"ja": "メールソフトを開きました。内容をご確認のうえ送信してください。", "en": "Your email client has opened. Please review and send."},
    "form.sent_from": {"ja": "UchUchU 問い合わせフォームより送信", "en": "Sent from the UchUchU contact form"},
    "form.privacy": {
        "ja": "いただいた情報はお問い合わせへの対応のみに使用します。第三者へ提供することはありません。",
        "en": "Your information is used only to respond to your inquiry and is never shared with third parties."},

    "home.title": {"ja": "宇宙開発ニュース・打ち上げ予定", "en": "Space News & Launch Schedule"},
    "home.next_launch": {"ja": "次の打ち上げ", "en": "Next Launches"},
    "home.featured": {"ja": "注目のニュース", "en": "Top Stories"},
    "home.by_topic": {"ja": "トピックから探す", "en": "Browse by Topic"},
    "nav.contact": {"ja": "お問い合わせ", "en": "Contact"},
    "nav.advertise": {"ja": "広告掲載", "en": "Advertise"},

    "contact.title": {"ja": "お問い合わせ", "en": "Contact"},
    "contact.subtitle": {
        "ja": "下記フォームよりお送りください。通常2営業日以内にご返信します。",
        "en": "Send us a message below. We usually reply within two business days."},
    "contact.send": {"ja": "メールを作成", "en": "Compose email"},
    "contact.direct": {"ja": "直接ご連絡", "en": "Direct contact"},
    "contact.note": {
        "ja": "通常2営業日以内に、ご入力いただいたメールアドレス宛にご返信します。",
        "en": "We usually reply within two business days."},
    "contact.operator": {"ja": "運営", "en": "Operator"},
    "contact.operator_note": {
        "ja": "UchUchUは株式会社TOEが運営する宇宙産業のサプライチェーン・メディアです。",
        "en": "UchUchU is a space industry supply chain media operated by TOE Inc."},

    "ad.title": {"ja": "広告掲載のご案内", "en": "Advertise with UchUchU"},
    "ad.subtitle": {
        "ja": "宇宙産業への参入を検討する製造業に、直接届く媒体です。",
        "en": "Reach manufacturers evaluating entry into the space supply chain."},
    "ad.audience": {"ja": "どなたに届くか", "en": "Who you reach"},
    "ad.audience_lead": {
        "ja": "UchUchUは一般の宇宙ファン向けメディアではありません。宇宙産業で事業機会を探す実務者に向けて編集しています。",
        "en": "UchUchU is not a general space-enthusiast media. It is edited for professionals seeking business opportunities in the space industry."},
    "ad.content": {"ja": "掲載コンテンツ", "en": "Content"},
    "ad.stats_note": {
        "ja": "2026年7月開設。掲載社数・記事数は随時拡充しています。アクセス実績はご要望に応じて開示します。",
        "en": "Launched July 2026. Traffic figures available on request."},
    "ad.menu": {"ja": "広告メニュー", "en": "Advertising options"},
    "ad.menu_note": {
        "ja": "掲載内容は編集部と協議のうえ決定します。事実と異なる内容・誇大な表現は掲載できません。",
        "en": "Content is agreed with our editorial team. We cannot publish inaccurate or exaggerated claims."},
    "ad.cta_title": {"ja": "まずはご相談ください", "en": "Get in touch"},
    "ad.cta_body": {
        "ja": "予算・目的をお聞かせいただければ、適した掲載方法をご提案します。媒体資料が必要な場合もお申し付けください。",
        "en": "Tell us your budget and goals and we will propose a suitable format."},
    "ad.cta_button": {"ja": "広告について問い合わせる", "en": "Contact us about advertising"},

    "nav.companies": {"ja": "企業DB", "en": "Companies"},
    "companies.title": {"ja": "宇宙産業 企業データベース", "en": "Space Industry Company Database"},
    "companies.subtitle": {
        "ja": "日本の宇宙産業に関わる企業を、事業領域別に整理しています。参入検討・取引先探索にお使いください。",
        "en": "Japanese companies in the space industry, organised by business area."},
    "companies.hq": {"ja": "本社", "en": "HQ"},
    "companies.official": {"ja": "公式サイト", "en": "Official site"},
    "companies.cta": {
        "ja": "掲載のご依頼・情報の修正は、お問い合わせよりご連絡ください。掲載は無料です。",
        "en": "To be listed or to correct information, please contact us. Listing is free."},

    "nav.topics": {"ja": "トピック", "en": "Topics"},
    "topic.other": {"ja": "他のトピック", "en": "Other topics"},
    "topic.count": {"ja": "{n}件の記事", "en": "{n} articles"},

    "home.latest_news": {"ja": "最新ニュース", "en": "Latest News"},
    "home.upcoming_launches": {"ja": "次の打ち上げ", "en": "Upcoming Launches"},
    "home.features": {"ja": "特集記事", "en": "Featured Articles"},
    "home.research": {"ja": "最新の研究動向", "en": "Latest Research"},
    "home.view_all": {"ja": "すべて見る", "en": "View all"},

    "news.title": {"ja": "宇宙開発ニュース", "en": "Space News"},
    "news.subtitle": {"ja": "国内外の公式発表とメディアを横断して集約。",
                      "en": "Aggregated from official and media sources worldwide."},
    "news.read_source": {"ja": "元記事を読む", "en": "Read source"},
    "news.filter_by_source": {"ja": "配信元で絞り込む", "en": "Filter by source"},
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

    "nav.faq": {"ja": "よくある質問", "en": "FAQ"},
    "nav.search": {"ja": "検索", "en": "Search"},

    "search.title": {"ja": "サイト内検索", "en": "Search"},
    "search.subtitle": {"ja": "ニュース・打ち上げ・研究動向・特集を横断して検索します。",
                        "en": "Search across news, launches, research, and features."},
    "search.placeholder": {"ja": "キーワードを入力（例: 月着陸、Starship）",
                           "en": "Type a keyword (e.g. lunar lander, Starship)"},
    "search.prompt": {"ja": "キーワードを入力してください。", "en": "Enter a keyword to search."},
    "search.loading": {"ja": "読み込み中…", "en": "Loading…"},
    "search.hits": {"ja": "{n}件見つかりました", "en": "{n} results"},
    "search.none": {"ja": "該当する項目がありませんでした。", "en": "No results found."},

    "faq.title": {"ja": "よくある質問", "en": "Frequently Asked Questions"},

    "pager.prev": {"ja": "前へ", "en": "Previous"},
    "pager.next": {"ja": "次へ", "en": "Next"},
    "pager.page": {"ja": "ページ", "en": "Page"},

    "meta.machine_translated": {"ja": "自動翻訳", "en": "Machine translated"},
    "meta.mt_note": {
        "ja": "海外ソースの記事は、この場で自動翻訳して掲載しています（機械翻訳のため訳文が不正確な場合があります）。正確な内容は各記事の元記事をご確認ください。",
        "en": "Articles from non-English sources are machine translated. Please refer to the original article for accuracy.",
    },
    "detail.related": {"ja": "関連するニュース", "en": "Related news"},
    "detail.back": {"ja": "ニュース一覧へ戻る", "en": "Back to news"},
    "detail.cta_title": {"ja": "この分野の企業を探していますか？", "en": "Looking for companies in this field?"},
    "detail.cta_body": {
        "ja": "UchUchUは宇宙産業に関わる日本企業をデータベース化しています。参入検討・取引先探索にお使いください。",
        "en": "UchUchU maintains a database of Japanese companies in the space industry."},

    "meta.stock_image": {"ja": "イメージ", "en": "Illustrative image"},
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
