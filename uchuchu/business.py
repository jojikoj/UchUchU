"""問い合わせ導線と広告メニューの定義。

このサイトの目的は「製造業からの広告掲載・相談を獲得すること」。
コンテンツをいくら積んでも受け皿がなければ成果はゼロなので、
用件別の問い合わせ導線と、広告主向けの媒体情報をここで一元管理する。

静的サイトのためサーバー側でフォームを受けられない。
mailto: に件名と本文を事前入力し、送信のハードルを下げる方式をとる。
"""
from __future__ import annotations

import urllib.parse

from . import config


def mailto(subject: str, body: str = "") -> str:
    """かつてmailto導線を出していた名残。

    サイト上にメールアドレスを出さない方針にしたため、
    問い合わせページへのリンクを返す。
    """
    return "../contact/"


# --- 用件別の問い合わせ ------------------------------------------------
_BODY_COMMON = "\n\n――――――――――\n貴社名：\nご担当者名：\nご連絡先：\n\nご用件：\n"

CONTACT_KINDS = {
    "ja": [
        {
            "label": "広告掲載について",
            "desc": "タイアップ記事・企業DB掲載枠など、広告メニューのご相談。",
            "subject": "[UchUchU] 広告掲載について",
            "body": "UchUchUへの広告掲載を検討しています。" + _BODY_COMMON,
        },
        {
            "label": "企業データベースへの掲載",
            "desc": "宇宙産業に関わる企業の新規掲載・情報修正のご依頼（掲載無料）。",
            "subject": "[UchUchU] 企業データベース掲載依頼",
            "body": "企業データベースへの掲載を希望します。"
                    "\n\n会社名：\n事業領域：\n公式サイトURL：\n本社所在地：\n"
                    "事業内容（100字程度）：\n" + _BODY_COMMON,
        },
        {
            "label": "宇宙産業への参入相談",
            "desc": "自社技術が宇宙産業で活きるか、何から着手すべきかのご相談。",
            "subject": "[UchUchU] 宇宙産業への参入について",
            "body": "宇宙産業への参入を検討しています。"
                    "\n\n自社の主な技術・加工分野：\n現在の主な取引先業界：\n"
                    "取得している認証（ISO 9001 等）：\n" + _BODY_COMMON,
        },
        {
            "label": "取材・情報提供",
            "desc": "記事化のご提案、プレスリリース、掲載内容の訂正依頼。",
            "subject": "[UchUchU] 取材・情報提供",
            "body": "情報提供・取材のご連絡です。" + _BODY_COMMON,
        },
    ],
    "en": [
        {
            "label": "Advertising",
            "desc": "Sponsored articles and company database placement.",
            "subject": "[UchUchU] Advertising inquiry",
            "body": "I would like to discuss advertising on UchUchU.\n\nCompany:\nName:\nContact:\n",
        },
        {
            "label": "Company database listing",
            "desc": "Request a new listing or correct existing information (free).",
            "subject": "[UchUchU] Company database listing",
            "body": "I would like to be listed in the company database.\n\n"
                    "Company:\nBusiness area:\nWebsite:\nHQ:\n",
        },
        {
            "label": "Press & tips",
            "desc": "Story suggestions, press releases, and corrections.",
            "subject": "[UchUchU] Press / tip",
            "body": "I have information to share.\n\nCompany:\nName:\nContact:\n",
        },
    ],
}


def contact_kinds(lang: str) -> list[dict]:
    out = []
    for k in CONTACT_KINDS.get(lang, CONTACT_KINDS["ja"]):
        item = dict(k)
        item["href"] = mailto(k["subject"], k["body"])
        out.append(item)
    return out


# --- 媒体情報（広告主向け）--------------------------------------------
# 読者数ではなく読者の質で構成する。
# PVを誇示できる段階ではないため、誇張せず現状を正確に示す。
AD_AUDIENCE = {
    "ja": [
        "宇宙産業への参入を検討する製造業の経営者・新規事業担当",
        "宇宙機器のサプライヤーを探す宇宙ベンチャー・研究機関",
        "部品調達・技術提携先を探す航空宇宙分野の調達担当",
        "宇宙産業の動向を追う投資家・自治体・産業支援機関",
    ],
    "en": [
        "Manufacturing executives evaluating entry into the space supply chain",
        "Space ventures and research institutes sourcing suppliers",
        "Procurement staff in aerospace seeking partners",
        "Investors and regional agencies tracking the space industry",
    ],
}

# 料金は載せない（サイトには出さず、問い合わせ時に個別提示する方針）。
# メニューは「何ができるか」と「誰に効くか」で構成する。
AD_MENU = {
    "ja": [
        {
            "name": "タイアップ記事",
            "desc": "貴社の技術・製品を、宇宙産業の文脈で解説する記事を編集部が制作します。"
                    "広告然としたPRではなく読み物として成立させ、読了率を確保します。"
                    "記事は掲載後も資産として残り、検索経由で継続的に読まれます。"
                    "サプライヤーを探す宇宙企業にも、参入を検討する製造業にも届きます。",
        },
        {
            "name": "企業データベース 上位掲載",
            "desc": "企業データベースの上部に固定表示し、ロゴ・詳細説明・問い合わせ導線を付与します。"
                    "サプライヤーを探す宇宙企業と、取引先を探す製造業の双方が見る場に、優先的に露出します。",
        },
        {
            "name": "レポート・調査の共同制作",
            "desc": "宇宙産業に関する調査レポートを共同で制作し、貴社名義で公開します。"
                    "見込み顧客の獲得（リードジェネレーション）を目的とする場合に適します。",
        },
    ],
    "en": [
        {
            "name": "Sponsored article",
            "desc": "Our editorial team writes an article explaining your technology "
                    "in the context of the space industry — read by both suppliers "
                    "and space companies.",
        },
        {
            "name": "Featured database placement",
            "desc": "Featured placement at the top of the company database with logo "
                    "and inquiry link.",
        },
        {
            "name": "Co-produced research",
            "desc": "We co-produce and publish research reports under your name.",
        },
    ],
}


def ad_mailto() -> str:
    return mailto(
        "[UchUchU] 広告掲載について",
        "UchUchUへの広告掲載を検討しています。"
        "\n\n希望メニュー（タイアップ記事／PR枠／レポート共同制作）：\n"
        "ご検討中の時期：\n" + _BODY_COMMON,
    )


# --- 運営会社ページ ---------------------------------------------------
# 「誰が何のために書いているか」を明示する。
# 匿名のまとめサイトと同じ扱いを受けないための、実務上の必須要素。
ABOUT_WHY = {
    "ja": [
        "株式会社TOEは福岡を拠点に、Web制作とAI開発を手がけています。"
        "その中で製造業のお客様と接する機会が多く、"
        "高い技術を持ちながら「宇宙産業は自分たちとは関係のない世界だ」と"
        "考えている企業が少なくないことを知りました。",
        "実際には、宇宙産業が必要としているものの多くは、"
        "精密加工・機構設計・品質管理といった、"
        "日本の製造業がすでに持っている能力です。"
        "足りていないのは技術ではなく、"
        "「どこに需要があり、何を求められ、誰に話を持っていけばよいか」という情報でした。",
        "UchUchUは、その情報の空白を埋めるために作りました。"
        "宇宙開発のニュースを追うだけでなく、"
        "それが自社の仕事にどうつながるのかまで書くことを方針としています。",
    ],
    "en": [
        "TOE Inc. is a Fukuoka-based company working in web production and AI development.",
        "Through our work with manufacturers, we found that many capable companies "
        "assume the space industry is unrelated to them — when in fact the industry "
        "needs precisely the skills they already have.",
        "UchUchU exists to close that information gap.",
    ],
}

EDITORIAL_POLICY = {
    "ja": [
        "事実と推測を分けて書きます。断定できないことは断定しません。",
        "誇張しません。参入が難しい点は難しいと書きます。",
        "記事は公開情報をもとに編集部が整理し、出典を明示します。",
        "広告記事は広告と分かる形で掲載し、"
        "事実と異なる内容・誇大な表現は掲載しません。",
        "企業データベースへの掲載は無料で、掲載料による順位付けは行いません。",
        "誤りの指摘は歓迎します。確認のうえ訂正し、訂正した旨を残します。",
    ],
    "en": [
        "We separate fact from inference and do not overstate.",
        "Articles are compiled from public sources with attribution.",
        "Sponsored content is clearly labelled; we do not publish inaccurate claims.",
        "Database listings are free and never ranked by payment.",
        "We welcome corrections and record them when made.",
    ],
}
