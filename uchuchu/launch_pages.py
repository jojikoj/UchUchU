"""打ち上げ予定の「絞り込みページ」を作る材料。

なぜ要るか（2026-09-22 実測）:
  Search Console で UchUchU に実際に付いていた検索語は
  「jaxa launch schedule」「tanegashima launch schedule」「rocket lab next launch date」
  ＝「誰が／どこから／いつ打ち上げるか」を知りたい意図だった。
  ところが受け皿は /launches/ の1枚（世界の予定200件を時系列に並べただけ）で、
  順位は 48〜86 位。title にも本文にも「種子島」「JAXA」「Rocket Lab」の語が
  見出しとして立っていないので、その語で探す人に「このページが答え」だと伝わらない。

  ここでは同じ実データ（Launch Library 2）を、読者の探し方に合わせて
  「日本」「事業者別」「射場別」「月別」の入口に切り直す。中身は自作記事ではなく
  実データの一覧なので、他所に無い一覧（日本時間・時刻未定の明示・カレンダー購読）
  を厚くする方針（メディア事業部/共通/運用/レポート/2026-09-09）に沿う。

  薄いページを量産しないための歯止め:
    - 事業者・射場は、手元のデータに MIN_ITEMS 件以上あるものだけページにする
    - 月は、その月に MIN_ITEMS 件以上あるものだけ
    - 日本の打ち上げは件数に関係なく作る（このサイトの読者が最初に探す対象のため）
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

# 1ページを立てるのに必要な最少件数（予定＋実績）。
MIN_ITEMS = 3

# 事業者（Launch Library 2 の launch_service_provider.name）→ 表示名・slug。
# 表に無い事業者は英語名のまま、slug は機械生成。
PROVIDERS: dict[str, dict] = {
    "SpaceX": {"slug": "spacex", "ja": "スペースX（SpaceX）", "en": "SpaceX"},
    "Rocket Lab": {"slug": "rocket-lab", "ja": "ロケットラボ（Rocket Lab）", "en": "Rocket Lab"},
    "China Aerospace Science and Technology Corporation": {
        "slug": "casc", "ja": "中国航天科技集団（CASC）", "en": "CASC (China Aerospace Science and Technology Corporation)"},
    "China Aerospace Science and Industry Corporation": {
        "slug": "casic", "ja": "中国航天科工集団（CASIC）", "en": "CASIC"},
    "Indian Space Research Organization": {
        "slug": "isro", "ja": "インド宇宙研究機関（ISRO）", "en": "ISRO (Indian Space Research Organisation)"},
    "Mitsubishi Heavy Industries": {
        "slug": "mhi", "ja": "三菱重工業（H3ロケット）", "en": "Mitsubishi Heavy Industries (H3)"},
    "Japan Aerospace Exploration Agency": {
        "slug": "jaxa", "ja": "JAXA（宇宙航空研究開発機構）", "en": "JAXA"},
    "Arianespace": {"slug": "arianespace", "ja": "アリアンスペース（Arianespace）", "en": "Arianespace"},
    "Firefly Aerospace": {"slug": "firefly", "ja": "ファイアフライ・エアロスペース", "en": "Firefly Aerospace"},
    "United Launch Alliance": {"slug": "ula", "ja": "ULA（ユナイテッド・ローンチ・アライアンス）", "en": "United Launch Alliance (ULA)"},
    "Isar Aerospace": {"slug": "isar-aerospace", "ja": "イザール・エアロスペース（Isar Aerospace）", "en": "Isar Aerospace"},
    "Russian Federal Space Agency (ROSCOSMOS)": {"slug": "roscosmos", "ja": "ロスコスモス（ROSCOSMOS）", "en": "Roscosmos"},
    "European Space Agency": {"slug": "esa", "ja": "欧州宇宙機関（ESA）", "en": "European Space Agency (ESA)"},
    "Blue Origin": {"slug": "blue-origin", "ja": "ブルーオリジン（Blue Origin）", "en": "Blue Origin"},
    "Northrop Grumman Space Systems": {"slug": "northrop-grumman", "ja": "ノースロップ・グラマン", "en": "Northrop Grumman"},
    "Space One": {"slug": "space-one", "ja": "スペースワン（カイロス）", "en": "Space One (KAIROS)"},
    "Interstellar Technologies": {"slug": "interstellar", "ja": "インターステラテクノロジズ", "en": "Interstellar Technologies"},
    "Korea Aerospace Research Institute": {"slug": "kari", "ja": "韓国航空宇宙研究院（KARI）", "en": "KARI"},
    "Gilmour Space Technologies": {"slug": "gilmour-space", "ja": "ギルモア・スペース", "en": "Gilmour Space"},
    "Rocket Factory Augsburg": {"slug": "rfa", "ja": "RFA（Rocket Factory Augsburg）", "en": "Rocket Factory Augsburg"},
    "Relativity Space": {"slug": "relativity", "ja": "レラティビティ・スペース", "en": "Relativity Space"},
    "Galactic Energy": {"slug": "galactic-energy", "ja": "星河動力（Galactic Energy）", "en": "Galactic Energy"},
    "LandSpace": {"slug": "landspace", "ja": "藍箭航天（LandSpace）", "en": "LandSpace"},
    "Space Pioneer": {"slug": "space-pioneer", "ja": "天兵科技（Space Pioneer）", "en": "Space Pioneer"},
    "CAS Space": {"slug": "cas-space", "ja": "中科宇航（CAS Space）", "en": "CAS Space"},
    "ExPace": {"slug": "expace", "ja": "航天科工火箭（ExPace）", "en": "ExPace"},
    "HyImpulse": {"slug": "hyimpulse", "ja": "HyImpulse", "en": "HyImpulse"},
    "PLD Space": {"slug": "pld-space", "ja": "PLD Space", "en": "PLD Space"},
    "Skyroot Aerospace": {"slug": "skyroot", "ja": "Skyroot Aerospace", "en": "Skyroot Aerospace"},
    "Astra Space": {"slug": "astra", "ja": "Astra", "en": "Astra"},
    "Orbex": {"slug": "orbex", "ja": "Orbex", "en": "Orbex"},
    "Orienspace Technology": {"slug": "orienspace", "ja": "東方空間（Orienspace）", "en": "Orienspace"},
}

# 射場（Launch Library 2 の pad.location.name）→ 表示名・slug。
SITES: dict[str, dict] = {
    "Tanegashima Space Center, Japan": {"slug": "tanegashima", "ja": "種子島宇宙センター", "en": "Tanegashima Space Center"},
    "Uchinoura Space Center, Japan": {"slug": "uchinoura", "ja": "内之浦宇宙空間観測所", "en": "Uchinoura Space Center"},
    "Taiki Aerospace Research Field, Japan": {"slug": "taiki", "ja": "北海道スペースポート（大樹町）", "en": "Hokkaido Spaceport (Taiki)"},
    "Spaceport Kii, Japan": {"slug": "kii", "ja": "スペースポート紀伊", "en": "Spaceport Kii"},
    "Vandenberg SFB, CA, USA": {"slug": "vandenberg", "ja": "ヴァンデンバーグ宇宙軍基地（米国）", "en": "Vandenberg Space Force Base"},
    "Cape Canaveral SFS, FL, USA": {"slug": "cape-canaveral", "ja": "ケープカナベラル宇宙軍基地（米国）", "en": "Cape Canaveral Space Force Station"},
    "Kennedy Space Center, FL, USA": {"slug": "kennedy", "ja": "ケネディ宇宙センター（米国）", "en": "Kennedy Space Center"},
    "Rocket Lab Launch Complex 1, Mahia Peninsula, New Zealand": {
        "slug": "mahia", "ja": "ロケットラボ第1発射場（ニュージーランド・マヒア）", "en": "Rocket Lab Launch Complex 1, Mahia"},
    "Rocket Lab Launch Complex 2, Wallops Island, Virginia, USA": {
        "slug": "wallops-lc2", "ja": "ロケットラボ第2発射場（ワロップス）", "en": "Rocket Lab Launch Complex 2, Wallops"},
    "Satish Dhawan Space Centre, India": {"slug": "satish-dhawan", "ja": "サティシュ・ダワン宇宙センター（インド）", "en": "Satish Dhawan Space Centre"},
    "Guiana Space Centre, French Guiana": {"slug": "kourou", "ja": "ギアナ宇宙センター（クールー）", "en": "Guiana Space Centre (Kourou)"},
    "Wenchang Space Launch Site, People's Republic of China": {"slug": "wenchang", "ja": "文昌衛星発射場（中国）", "en": "Wenchang Space Launch Site"},
    "Jiuquan Satellite Launch Center, People's Republic of China": {"slug": "jiuquan", "ja": "酒泉衛星発射センター（中国）", "en": "Jiuquan Satellite Launch Center"},
    "Xichang Satellite Launch Center, People's Republic of China": {"slug": "xichang", "ja": "西昌衛星発射センター（中国）", "en": "Xichang Satellite Launch Center"},
    "Taiyuan Satellite Launch Center, People's Republic of China": {"slug": "taiyuan", "ja": "太原衛星発射センター（中国）", "en": "Taiyuan Satellite Launch Center"},
    "Wallops Flight Facility, Virginia, USA": {"slug": "wallops", "ja": "ワロップス飛行施設（米国）", "en": "Wallops Flight Facility"},
    "Andøya Spaceport": {"slug": "andoya", "ja": "アンドーヤ・スペースポート（ノルウェー）", "en": "Andøya Spaceport"},
    "SpaceX Starbase, TX, USA": {"slug": "starbase", "ja": "スターベース（米国テキサス）", "en": "SpaceX Starbase"},
    "Baikonur Cosmodrome, Republic of Kazakhstan": {"slug": "baikonur", "ja": "バイコヌール宇宙基地", "en": "Baikonur Cosmodrome"},
    "Plesetsk Cosmodrome, Russian Federation": {"slug": "plesetsk", "ja": "プレセツク宇宙基地", "en": "Plesetsk Cosmodrome"},
    "Vostochny Cosmodrome, Siberia, Russian Federation": {"slug": "vostochny", "ja": "ボストーチヌイ宇宙基地", "en": "Vostochny Cosmodrome"},
    "Pacific Spaceport Complex, Alaska, USA": {"slug": "kodiak", "ja": "太平洋宇宙港（アラスカ・コディアック）", "en": "Pacific Spaceport Complex (Kodiak)"},
    "Esrange Space Center, Sweden": {"slug": "esrange", "ja": "エスレンジ（スウェーデン）", "en": "Esrange Space Center"},
    "SaxaVord Spaceport, UK": {"slug": "saxavord", "ja": "サクサボード・スペースポート（英国）", "en": "SaxaVord Spaceport"},
    "Alcântara Space Center, Federative Republic of Brazil": {"slug": "alcantara", "ja": "アルカンタラ宇宙センター（ブラジル）", "en": "Alcântara Space Center"},
    "Naro Space Center, South Korea": {"slug": "naro", "ja": "羅老宇宙センター（韓国）", "en": "Naro Space Center"},
    "Haiyang Oriental Spaceport": {"slug": "haiyang", "ja": "海陽東方航天港（中国・海上発射）", "en": "Haiyang Oriental Spaceport"},
}

_EN_MONTHS = ["", "January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "other"


def _provider_meta(name: str) -> dict:
    m = PROVIDERS.get(name)
    if m:
        return m
    return {"slug": slugify(name), "ja": name, "en": name}


def _site_meta(name: str) -> dict:
    m = SITES.get(name)
    if m:
        return m
    # 「Xxx, Country」の先頭要素で slug を作る（長い正式名は URL に向かない）
    return {"slug": slugify((name or "").split(",")[0]), "ja": name, "en": name}


def _month_key(it: dict, lang: str) -> str | None:
    """その打ち上げが属する月（YYYY-MM）。日本語サイトは日本時間で切る。"""
    net = it.get("net")
    if not net:
        return None
    try:
        dt = datetime.fromisoformat(net.replace("Z", "+00:00"))
    except ValueError:
        return None
    tz = JST if lang == "ja" else timezone.utc
    local = dt.astimezone(tz)
    return f"{local.year:04d}-{local.month:02d}"


def _month_label(key: str, lang: str) -> str:
    y, m = key.split("-")
    return f"{int(y)}年{int(m)}月" if lang == "ja" else f"{_EN_MONTHS[int(m)]} {y}"


def build_filter_pages(launches: list[dict], lang: str, now: datetime) -> list[dict]:
    """絞り込みページの定義を返す。

    各要素: path（launches/ からの相対。末尾スラッシュ）, kind, key, name,
            items（prepare_launches 済みの打ち上げ）, title, h1, lead, ics_label
    """
    pages: list[dict] = []
    ja = lang == "ja"

    # --- 日本 -------------------------------------------------------------
    jp = [l for l in launches if l.get("is_japan")]
    pages.append(_page(lang, "launches/japan/", "japan", "japan",
                       "日本" if ja else "Japan", jp, now, always=True))

    # --- 事業者別 ---------------------------------------------------------
    by_provider: dict[str, list[dict]] = {}
    for l in launches:
        p = l.get("provider")
        if p:
            by_provider.setdefault(p, []).append(l)
    for name, items in sorted(by_provider.items(), key=lambda kv: -len(kv[1])):
        if len(items) < MIN_ITEMS:
            continue
        meta = _provider_meta(name)
        pages.append(_page(lang, f"launches/provider/{meta['slug']}/", "provider",
                           name, meta["ja" if ja else "en"], items, now))

    # --- 射場別 -----------------------------------------------------------
    by_site: dict[str, list[dict]] = {}
    for l in launches:
        s = l.get("location")
        if s:
            by_site.setdefault(s, []).append(l)
    for name, items in sorted(by_site.items(), key=lambda kv: -len(kv[1])):
        if len(items) < MIN_ITEMS:
            continue
        meta = _site_meta(name)
        pages.append(_page(lang, f"launches/site/{meta['slug']}/", "site",
                           name, meta["ja" if ja else "en"], items, now))

    # --- 月別 -------------------------------------------------------------
    by_month: dict[str, list[dict]] = {}
    for l in launches:
        k = _month_key(l, lang)
        if k:
            by_month.setdefault(k, []).append(l)
    for key in sorted(by_month):
        items = by_month[key]
        if len(items) < MIN_ITEMS:
            continue
        pages.append(_page(lang, f"launches/{key}/", "month", key,
                           _month_label(key, lang), items, now))

    # 重複 path（例: slug 衝突）は先勝ち
    seen: set[str] = set()
    out = []
    for p in pages:
        if p["path"] in seen:
            continue
        seen.add(p["path"])
        out.append(p)
    return out


def _page(lang: str, path: str, kind: str, key: str, name: str,
          items: list[dict], now: datetime, always: bool = False) -> dict:
    ja = lang == "ja"
    upcoming = [l for l in items if l.get("upcoming")]
    past = [l for l in items if not l.get("upcoming")]
    nxt = upcoming[0] if upcoming else None

    # 見出しは「読者が検索窓に打つ語」を先頭に置く。
    if kind == "japan":
        h1 = ("日本のロケット打ち上げ予定（JAXA・H3・イプシロン・種子島）" if ja
              else "Japan Rocket Launch Schedule — JAXA, H3, Epsilon, Tanegashima")
        title = ("日本のロケット打ち上げ予定【JAXA・H3・種子島】日本時間" if ja
                 else "Japan Rocket Launch Schedule (JAXA, H3, Epsilon)")
        ics = "日本の打ち上げをカレンダーに登録" if ja else "Add Japanese launches to your calendar"
    elif kind == "provider":
        h1 = (f"{name}の打ち上げ予定・次回の打ち上げ日時" if ja
              else f"{name} Launch Schedule — Next Launch Date & Time")
        title = (f"{name}の打ち上げ予定・次回はいつ【日本時間】" if ja
                 else f"{name} Launch Schedule & Next Launch")
        ics = (f"{name}の打ち上げをカレンダーに登録" if ja
               else f"Add {name} launches to your calendar")
    elif kind == "site":
        h1 = (f"{name}の打ち上げ予定" if ja else f"{name} Launch Schedule")
        title = (f"{name}の打ち上げ予定・次回はいつ【日本時間】" if ja
                 else f"{name} Launch Schedule — Upcoming Launches")
        ics = (f"{name}の打ち上げをカレンダーに登録" if ja
               else f"Add {name} launches to your calendar")
    else:  # month
        h1 = (f"{name}のロケット打ち上げ予定一覧" if ja
              else f"Rocket Launches in {name} — Full Schedule")
        title = (f"{name}のロケット打ち上げ予定一覧【日本時間】" if ja
                 else f"Rocket Launches in {name}")
        ics = "この月の打ち上げをカレンダーに登録" if ja else "Add this month's launches to your calendar"

    # リード文は実データからだけ作る（件数・次回・射場）。
    # description（検索結果の説明文）は同じ材料で短く別に作る（120字前後）。
    if ja:
        loc = _site_meta(nxt["location"])["ja"] if nxt and nxt.get("location") else ""
        where = f"、{loc}" if loc and kind != "site" else ""
        head = (f"{name}の打ち上げ予定{len(upcoming)}件と直近の結果{len(past)}件を日本時間で掲載。"
                if kind != "month" else
                f"{name}に予定・実施されたロケット打ち上げ{len(items)}件を日本時間で一覧。")
        nxt_s = f"次回は{nxt.get('name')}（{nxt.get('net_short')}{where}）。" if nxt else ""
        lead = head + nxt_s + "時刻が決まっていない打ち上げは「時刻未定」と明示し、毎日更新しています。"
        desc = head + nxt_s + "カレンダー購読可。"
    else:
        loc = nxt.get("location") if nxt else ""
        where = f" from {loc}" if loc and kind != "site" else ""
        head = (f"{len(upcoming)} upcoming launches and {len(past)} recent results for {name}, times in UTC."
                if kind != "month" else
                f"All {len(items)} rocket launches scheduled or flown in {name}, times in UTC.")
        nxt_s = f" Next: {nxt.get('name')} ({nxt.get('net_short')}{where})." if nxt else ""
        lead = head + nxt_s + " Launches without a fixed time are marked TBD. Updated daily."
        desc = head + nxt_s + " Calendar subscription available."

    return {
        "path": path, "kind": kind, "key": key, "name": name,
        "launches": items, "upcoming": upcoming, "past": past, "next": nxt,
        "title": title, "h1": h1, "lead": lead, "desc": desc, "ics_label": ics,
        "always": always,
    }


def nav_for(pages: list[dict], lang: str, current: str | None) -> dict:
    """絞り込みチップ。path は言語ルート基準（テンプレ側で rel を前置する）。"""
    ja = lang == "ja"

    def entry(p: dict) -> dict:
        return {"href": p["path"], "name": p["name"], "current": p["path"] == current,
                "n": len(p["upcoming"])}

    rows = [{"label": "", "entries": [
        {"href": "launches/", "name": "すべて" if ja else "All", "current": current == "launches/", "n": None},
        *[entry(p) for p in pages if p["kind"] == "japan"],
    ]}]
    for kind, label_ja, label_en in (("provider", "事業者別", "By provider"),
                                     ("site", "射場別", "By launch site"),
                                     ("month", "月別", "By month")):
        items = [entry(p) for p in pages if p["kind"] == kind]
        if items:
            rows.append({"label": label_ja if ja else label_en, "entries": items})
    return {"rows": rows}


def signature(items: list[dict]) -> str:
    """ページに載る打ち上げの「中身」を表す指紋。lastmod の判定に使う。

    id・予定時刻・状態・予定/実績の別が1つでも変われば別物とみなす。
    カウントダウンの文字列は含めない（毎日変わるが「更新」ではない）。
    """
    import hashlib
    key = "|".join(f"{l.get('id')}:{l.get('net')}:{l.get('status_name')}:{int(bool(l.get('upcoming')))}"
                   for l in items)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
