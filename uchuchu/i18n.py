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
    "nav.procurement": {"ja": "調達情報", "en": "Procurement"},

    # 調達情報。読者を「参入したい製造業」と「サプライヤーを探す宇宙企業」に
    # 絞ったとき、両者が毎日確認する唯一の実務情報。
    "procurement.title": {"ja": "宇宙分野の調達・入札情報",
                          "en": "Space Sector Procurement (Japan)"},
    "procurement.subtitle": {
        "ja": "JAXA・内閣府・省庁が公告した宇宙関連の調達案件。官公需情報ポータルサイト（中小企業庁）から毎日集めています。",
        "en": "Space-related public tenders in Japan, collected daily from the government procurement portal."},
    "procurement.org": {"ja": "発注機関", "en": "Organisation"},
    "procurement.issued": {"ja": "公告日", "en": "Issued"},
    "procurement.area": {"ja": "所在地", "en": "Area"},
    "procurement.doc": {"ja": "公告文書を見る", "en": "View the notice"},
    "procurement.jaxa_only": {"ja": "JAXA", "en": "JAXA"},
    "procurement.note": {
        "ja": "掲載期間を過ぎた案件は、発注機関側で文書が削除されている場合があります。応札の可否・期限は必ず発注機関の公告でご確認ください。",
        "en": "Notices may be removed by the issuing organisation after their posting period. Always verify details with the original notice."},
    "procurement.recent": {"ja": "新着の調達", "en": "Recent tenders"},

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
    # 企業DBの掲載申込リンクが選ぶ用件。問い合わせフォームの選択肢の値と一致させること。
    "form.kind_listing": {"ja": "企業データベースへの掲載", "en": "Company database listing"},
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

    "about.title": {"ja": "運営会社", "en": "About us"},
    "about.subtitle": {
        "ja": "UchUchUは株式会社TOEが運営する、宇宙産業のサプライチェーン・メディアです。",
        "en": "UchUchU is a space industry supply chain media operated by TOE Inc."},
    "about.why": {"ja": "なぜこのメディアを運営しているのか", "en": "Why we run this media"},
    "about.policy": {"ja": "編集方針", "en": "Editorial policy"},
    "about.profile": {"ja": "会社概要", "en": "Company profile"},
    "about.contact_lead": {
        "ja": "掲載・広告・取材のご相談はフォームから承っています。",
        "en": "Please use the form for listings, advertising, and press inquiries."},
    "contact.operator_note": {
        "ja": "UchUchUは株式会社TOEが運営する宇宙産業のサプライチェーン・メディアです。",
        "en": "UchUchU is a space industry supply chain media operated by TOE Inc."},

    "ad.title": {"ja": "広告掲載のご案内", "en": "Advertise with UchUchU"},
    "ad.subtitle": {
        "ja": "宇宙産業でサプライヤーを探す企業と、宇宙に参入したい製造業。その両者が集まる場です。",
        "en": "Where companies sourcing space suppliers meet manufacturers entering the industry."},
    "ad.audience": {"ja": "どなたに届くか", "en": "Who you reach"},
    "ad.audience_lead": {
        "ja": "UchUchUは一般の宇宙ファン向けメディアではありません。宇宙産業で事業機会を探す実務者に向けて編集しています。",
        "en": "UchUchU is not a general space-enthusiast media. It is edited for professionals seeking business opportunities in the space industry."},
    # 広告主が「なぜここに出すのか」を、立場別に明示する。
    # 本命は、サプライヤーを探す宇宙企業。
    "ad.why_title": {"ja": "なぜUchUchUに出すのか", "en": "Why advertise here"},
    "ad.why_space": {
        "ja": "サプライヤーを探す宇宙企業へ — 部品・素材・加工・試験設備の作り手が読む媒体です。「こういう部品を作れる会社を探している」を、参入意欲の高い製造業に直接届けられます。",
        "en": "For space companies sourcing suppliers — reach manufacturers of parts, materials, machining, and test equipment who are actively looking to enter the space supply chain."},
    "ad.why_maker": {
        "ja": "自社を売り込みたい製造業へ — 「宇宙で使える技術を持っている」ことを、発注側の宇宙企業や同業に見つけてもらえます。企業データベースへの掲載は無料です。",
        "en": "For manufacturers — let space companies and peers discover that your technology can be used in space. Database listing is free."},
    "ad.content": {"ja": "掲載コンテンツ", "en": "Content"},
    "ad.stats_note": {
        "ja": "2026年7月開設。掲載社数・記事数は随時拡充しています。アクセス実績はご要望に応じて開示します。",
        "en": "Launched July 2026. Listings and articles are growing. Traffic figures available on request."},
    "ad.menu": {"ja": "掲載メニュー", "en": "Options"},
    "ad.menu_note": {
        "ja": "料金は目的・内容に応じて個別にご案内します。掲載内容は編集部と協議のうえ決定し、事実と異なる内容・誇大な表現は掲載できません。",
        "en": "Pricing is quoted individually. Content is agreed with our editorial team; we cannot publish inaccurate or exaggerated claims."},
    "ad.cta_title": {"ja": "まずはご相談ください", "en": "Get in touch"},
    "ad.cta_body": {
        "ja": "目的をお聞かせいただければ、適した掲載方法と料金をご提案します。媒体資料が必要な場合もお申し付けください。",
        "en": "Tell us your goal and we will propose a suitable format and price. Media kit available on request."},
    "ad.cta_button": {"ja": "広告について問い合わせる", "en": "Contact us about advertising"},

    "nav.companies": {"ja": "企業DB", "en": "Companies"},
    "companies.title": {"ja": "宇宙産業 企業データベース", "en": "Space Industry Company Database"},
    "companies.subtitle": {
        "ja": "宇宙産業に関わる企業を事業領域別に整理した一覧です。サプライヤーを探す宇宙企業の取引先探索に、また製造業が宇宙企業に見つけてもらう場としてお使いください。",
        "en": "Companies in the space industry by business area. Use it to source suppliers, or to be found by space companies."},
    "companies.list_free": {
        "ja": "掲載は無料・随時受付中",
        "en": "Free listing, open now"},
    "companies.join_title": {
        "ja": "貴社も掲載しませんか（無料）",
        "en": "List your company (free)"},
    "companies.join_body": {
        "ja": "宇宙分野で使える技術をお持ちなら、業種を問わず掲載できます。宇宙での実績は必要ありません。掲載された企業は、サプライヤーを探す宇宙企業の目に留まります。",
        "en": "If your technology can be used in space, you can be listed — no space track record required. Listed companies get found by space companies sourcing suppliers."},
    "companies.join_button": {
        "ja": "掲載を申し込む（無料）",
        "en": "Apply to be listed (free)"},
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
    "news.continue_at_source": {
        "ja": "※ 内容の紹介はここまでです。続きは元記事をご覧ください。",
        "en": "Introduction ends here. Please read the full article at the source."},
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
    "launches.today": {"ja": "今日の打ち上げ", "en": "Launching today"},
    "launches.this_week": {"ja": "今週", "en": "This week"},
    "launches.later": {"ja": "以降の予定", "en": "Later"},
    "launches.results": {"ja": "直近の結果", "en": "Recent results"},
    "launches.none_today": {"ja": "今日の打ち上げ予定はありません。",
                            "en": "No launches scheduled today."},
    "launches.ics": {"ja": "カレンダーに登録（購読）",
                     "en": "Subscribe in your calendar"},
    "launches.ics_note": {
        "ja": "カレンダーアプリに購読登録すると、打ち上げ予定が自動で更新されます。日程は変更されることがあります。",
        "en": "Subscribe once and the schedule updates automatically. Dates are subject to change."},
    "launches.tz_note": {"ja": "時刻は日本時間（括弧内はUTC）。",
                         "en": "Times are in UTC."},
    "launches.japan": {"ja": "日本の打ち上げ", "en": "Japanese launches"},
    "launches.time_tbd": {"ja": "時刻未定", "en": "time TBD"},

    # 「今日の宇宙」— 毎日ここだけ見れば今日の状況が分かる、が狙い。
    "today.title": {"ja": "今日の宇宙", "en": "Space Today"},
    "today.next": {"ja": "次の打ち上げ", "en": "Next launch"},
    "today.launches_today": {"ja": "今日の打ち上げ", "en": "Launches today"},
    "today.launches_week": {"ja": "今週の打ち上げ", "en": "Launches this week"},
    "today.results_24h": {"ja": "24時間以内の結果", "en": "Results in 24h"},
    "today.news_today": {"ja": "24時間のニュース", "en": "News in 24h"},
    "today.unit": {"ja": "件", "en": ""},
    "today.success": {"ja": "成功", "en": "Success"},
    "today.failure": {"ja": "失敗", "en": "Failure"},
    "today.partial": {"ja": "部分的成功", "en": "Partial failure"},
    "today.updated": {"ja": "最終更新", "en": "Updated"},
    "today.no_result": {"ja": "24時間以内に完了した打ち上げはありません。",
                        "en": "No launches completed in the past 24 hours."},

    "papers.title": {"ja": "研究動向", "en": "Research Trends"},
    "papers.subtitle": {"ja": "宇宙工学・惑星科学・宇宙物理の最新プレプリント。",
                        "en": "Latest preprints in space engineering and astrophysics."},
    "papers.authors": {"ja": "著者", "en": "Authors"},
    "papers.pdf": {"ja": "PDF", "en": "PDF"},
    "papers.abstract": {"ja": "概要", "en": "Abstract"},
    "papers.read": {"ja": "詳細を見る", "en": "Read"},
    "papers.view_on_arxiv": {"ja": "arXivで全文を読む", "en": "Read full text on arXiv"},
    "papers.original_title": {"ja": "原題", "en": "Original title"},
    "papers.back": {"ja": "研究動向へ戻る", "en": "Back to research trends"},

    "articles.title": {"ja": "特集記事", "en": "Feature Articles"},
    "articles.subtitle": {"ja": "宇宙開発をわかりやすく掘り下げる読み物。",
                          "en": "In-depth reads that make space exploration clear."},
    "articles.read": {"ja": "続きを読む", "en": "Read more"},
    "articles.back": {"ja": "特集一覧へ戻る", "en": "Back to features"},
    "article.updated": {"ja": "更新", "en": "Updated"},

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
        "ja": "自動翻訳のため訳文が不正確な場合があります",
        "en": "Machine translated; wording may be inaccurate",
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
    # 運営元と、同じ仕組み（無料の公開データ＋自動更新）で動かしている姉妹メディア。
    "footer.network": {"ja": "運営元", "en": "Who runs this"},
    "footer.toe": {"ja": "株式会社TOE", "en": "TOE Inc."},
    "footer.aioni": {"ja": "AIの鬼 — AI実践・実測ラボ",
                     "en": "AI Oni — AI practice & measurement lab"},
}


def t(key: str, lang: str) -> str:
    entry = STRINGS.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get("en") or key
