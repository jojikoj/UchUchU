"""主題（トピック）分類。

集約した記事を「月」「火星」「ロケット」等の主題に自動分類する。
時系列一覧だけでは読者が関心のある領域にたどり着けないため、
カテゴリ導線・関連記事・注目トピックの土台としてこれを使う。

分類は収集時ではなくビルド時に行う。
キーワードを調整したら再収集せずに反映できるようにするため。
"""
from __future__ import annotations

import re

# 各トピック: id, 日英の表示名, 判定キーワード（日英）
# キーワードは小文字化した「タイトル＋要約」に対して部分一致で判定する。
TOPICS = [
    {
        "id": "moon",
        "name": {"ja": "月", "en": "Moon"},
        "desc": {"ja": "月探査・月着陸・アルテミス計画",
                 "en": "Lunar exploration, landings, and the Artemis program"},
        "keywords": [
            "moon", "lunar", "artemis", "cislunar", "regolith",
            "月", "月面", "月着陸", "アルテミス", "かぐや", "レゴリス",
        ],
    },
    {
        "id": "mars",
        "name": {"ja": "火星", "en": "Mars"},
        "desc": {"ja": "火星探査・火星探査車・有人火星計画",
                 "en": "Mars exploration, rovers, and crewed Mars plans"},
        "keywords": [
            "mars", "martian", "perseverance", "curiosity rover", "ingenuity",
            "火星", "パーサヴィアランス", "キュリオシティ",
        ],
    },
    {
        "id": "rocket",
        "name": {"ja": "ロケット", "en": "Rockets"},
        "desc": {"ja": "打ち上げ機・エンジン・再使用技術",
                 "en": "Launch vehicles, engines, and reusability"},
        "keywords": [
            "rocket", "launch vehicle", "starship", "falcon 9", "falcon heavy",
            "vulcan", "ariane", "electron", "new glenn", "booster", "first stage",
            "reusable", "static fire", "engine test", "h3", "h-iia", "epsilon",
            "ロケット", "打ち上げ", "打上げ", "スターシップ", "ファルコン",
            "再使用", "イプシロン", "燃焼試験", "エンジン",
        ],
    },
    {
        "id": "satellite",
        "name": {"ja": "衛星・地球観測", "en": "Satellites"},
        "desc": {"ja": "人工衛星・通信コンステレーション・地球観測",
                 "en": "Satellites, constellations, and Earth observation"},
        "keywords": [
            "satellite", "constellation", "starlink", "kuiper", "oneweb",
            "earth observation", "remote sensing", "smallsat", "cubesat",
            "gps", "navigation satellite", "weather satellite",
            "衛星", "コンステレーション", "スターリンク", "地球観測",
            "リモートセンシング", "小型衛星", "測位",
        ],
    },
    {
        "id": "human",
        "name": {"ja": "有人宇宙", "en": "Human Spaceflight"},
        "desc": {"ja": "宇宙飛行士・国際宇宙ステーション・宇宙滞在",
                 "en": "Astronauts, the ISS, and life in orbit"},
        "keywords": [
            "astronaut", "cosmonaut", "iss", "international space station",
            "spacewalk", "eva", "crew dragon", "soyuz", "space station",
            "tiangong", "human spaceflight", "space tourism",
            "宇宙飛行士", "国際宇宙ステーション", "船外活動", "有人",
            "宇宙旅行", "宇宙滞在", "きぼう",
        ],
    },
    {
        "id": "science",
        "name": {"ja": "宇宙科学", "en": "Space Science"},
        "desc": {"ja": "天体観測・惑星科学・宇宙物理",
                 "en": "Astronomy, planetary science, and astrophysics"},
        "keywords": [
            "telescope", "webb", "hubble", "galaxy", "black hole", "exoplanet",
            "asteroid", "comet", "jupiter", "saturn", "venus", "mercury",
            "neptune", "uranus", "pluto", "supernova", "nebula", "star",
            "dark matter", "dark energy", "cosmic", "astronomy", "astrophysic",
            "望遠鏡", "銀河", "ブラックホール", "系外惑星", "小惑星", "彗星",
            "木星", "土星", "金星", "超新星", "星雲", "恒星", "天文",
            "ダークマター", "はやぶさ",
        ],
    },
    {
        "id": "business",
        "name": {"ja": "宇宙ビジネス", "en": "Space Business"},
        "desc": {"ja": "資金調達・契約・宇宙産業の動向",
                 "en": "Funding, contracts, and the space industry"},
        "keywords": [
            "funding", "raises", "investment", "contract", "award", "billion",
            "million", "startup", "ipo", "acquisition", "merger", "revenue",
            "commercial", "partnership",
            "資金調達", "出資", "契約", "受注", "億円", "投資", "上場",
            "買収", "提携", "商業", "ビジネス", "事業",
        ],
    },
    {
        "id": "japan",
        "name": {"ja": "日本の宇宙開発", "en": "Japan in Space"},
        "desc": {"ja": "JAXA・国内企業・日本の宇宙政策",
                 "en": "JAXA, Japanese companies, and national space policy"},
        "keywords": [
            "jaxa", "japan", "japanese", "ispace", "astroscale", "interstellar",
            "h3 rocket", "hayabusa", "himawari", "tanegashima",
            "jaxa", "日本", "国内", "種子島", "内之浦", "ispace",
            "アストロスケール", "インターステラ", "はやぶさ", "ひまわり",
        ],
    },
]

TOPIC_BY_ID = {t["id"]: t for t in TOPICS}

# キーワードを事前にコンパイル（全記事×全キーワードを回すため）
_COMPILED = [
    (t["id"], [k.lower() for k in t["keywords"]])
    for t in TOPICS
]


def classify(title: str, summary: str = "", limit: int = 3) -> list[str]:
    """記事の主題IDを返す。該当が多い順に最大 limit 件。

    ヒット数でスコアリングし、1つも当たらなければ空リストを返す
    （無理に分類せず「その他」に落とす方が誤分類より害が小さい）。
    """
    blob = f"{title} {summary}".lower()
    if not blob.strip():
        return []
    scores: list[tuple[int, str]] = []
    for tid, kws in _COMPILED:
        hits = sum(1 for k in kws if k in blob)
        if hits:
            scores.append((hits, tid))
    if not scores:
        return []
    scores.sort(key=lambda x: -x[0])
    return [tid for _, tid in scores[:limit]]


def name(topic_id: str, lang: str) -> str:
    t = TOPIC_BY_ID.get(topic_id)
    return t["name"][lang] if t else topic_id


def desc(topic_id: str, lang: str) -> str:
    t = TOPIC_BY_ID.get(topic_id)
    return t["desc"][lang] if t else ""


def counts(items: list[dict]) -> dict[str, int]:
    """トピックごとの記事数。ナビの並び順や注目トピック抽出に使う。"""
    out: dict[str, int] = {}
    for it in items:
        for tid in it.get("topics", []):
            out[tid] = out.get(tid, 0) + 1
    return out
