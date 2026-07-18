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

AD_MENU = {
    "ja": [
        {
            "name": "タイアップ記事",
            "price": "20万円〜／本",
            "desc": "貴社の技術・製品を、宇宙産業の文脈で解説する記事を編集部が制作します。"
                    "広告然としたPRではなく、読み物として成立する内容にすることで読了率を確保します。"
                    "記事は掲載後も資産として残り、検索経由で継続的に読まれます。",
        },
        {
            "name": "企業データベース PR枠",
            "price": "月額1万円〜",
            "desc": "企業データベースの上部に固定表示し、ロゴ・詳細説明・問い合わせ導線を付与します。"
                    "参入検討中の製造業が取引先を探す場に、優先的に露出します。",
        },
        {
            "name": "レポート・調査の共同制作",
            "price": "個別見積",
            "desc": "宇宙産業に関する調査レポートを共同で制作し、貴社名義で公開します。"
                    "リード獲得を目的とする場合に適します。",
        },
    ],
    "en": [
        {
            "name": "Sponsored article",
            "price": "From ¥200,000",
            "desc": "Our editorial team writes an article explaining your technology "
                    "in the context of the space industry.",
        },
        {
            "name": "Database PR placement",
            "price": "From ¥10,000/month",
            "desc": "Featured placement at the top of the company database with logo "
                    "and inquiry link.",
        },
        {
            "name": "Co-produced research",
            "price": "On request",
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
