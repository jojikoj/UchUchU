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

import html as html_mod
import json
import os
import re
import shutil
from datetime import datetime, timedelta, timezone

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import business, companies, config, indexnow, seo, topics
from .i18n import t as _t


# --- データ読み込み -----------------------------------------------------
def _load_json(name: str) -> dict:
    path = config.DATA_DIR / name
    if not path.exists():
        return {"items": [], "generated_at": None}
    return json.loads(path.read_text(encoding="utf-8"))


def _display_width(s: str) -> float:
    """全角を1、半角を0.5として数えた表示幅。"""
    return sum(0.5 if (" " <= c <= "ÿ" or "｡" <= c <= "ﾟ") else 1
               for c in s)


def head_title(title: str, limit: float = 46) -> str:
    """<title> 用に題を丸める。h1 と OGP には使わない。

    論文ページ（/p/）は arXiv の英語原題をそのまま <title> に入れていて、
    2026-08-05 の実測では半角90〜130字（全角換算45〜65字）あった。
    検索結果はこの長さを表示しないので、後ろに付くサイト名まで含めて
    まるごと切られていた。h1 には原題を全文残す（正式名称なので省略しない）。

    英語は単語の途中で切ると読めなくなるため、空白で区切れる位置を優先する。
    """
    title = re.sub(r"\s+", " ", (title or "")).strip()
    if _display_width(title) <= limit:
        return title
    out = []
    w = 0.0
    for ch in title:
        cw = 0.5 if (" " <= ch <= "ÿ" or "｡" <= ch <= "ﾟ") else 1
        if w + cw > limit - 1:
            break
        out.append(ch)
        w += cw
    cut = "".join(out)
    # 単語の途中で終わったら、直前の区切りまで戻す（短くなりすぎない範囲で）
    pos = max(cut.rfind(" "), cut.rfind("："), cut.rfind(":"), cut.rfind("、"))
    if pos >= len(cut) // 2:
        cut = cut[:pos]
    return cut.rstrip(" ,:;-—–") + "…"


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


JST = timezone(timedelta(hours=9))


def fmt_date(iso: str | None, lang: str, with_time: bool = False) -> str | None:
    """日付の表示。日本語サイトの時刻は日本時間で出す。

    打ち上げ時刻を UTC だけで出していたが、日本の読者は毎回9時間を
    足して読む必要があり、予定として使えない。日本語サイトは JST を主、
    UTC を従にする（海外ソースとの照合のため UTC も残す）。
    """
    dt = _parse_iso(iso)
    if dt is None:
        return None
    if lang == "ja":
        local = dt.astimezone(JST)
        base = f"{local.year}年{local.month}月{local.day}日"
        if with_time:
            base += (f" {local.hour:02d}:{local.minute:02d} JST"
                     f"（{dt.hour:02d}:{dt.minute:02d} UTC）")
        return base
    base = f"{_EN_MONTHS[dt.month]} {dt.day}, {dt.year}"
    if with_time:
        base += f" {dt.hour:02d}:{dt.minute:02d} UTC"
    return base


_JA_WDAY = ["月", "火", "水", "木", "金", "土", "日"]
_EN_WDAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def fmt_date_short(iso: str | None, lang: str) -> str | None:
    """一覧用の短い絶対表記。

    「2時間前」のような相対表記は使わない。宇宙開発では打ち上げ日など
    日付そのものが情報価値を持ち、相対表記では予定と照合できないため。
    日本語サイトは日本時間で切る（日付がずれると予定表として使えない）。
    """
    dt = _parse_iso(iso)
    if dt is None:
        return None
    if lang == "ja":
        dt = dt.astimezone(JST)
    # メディアで一般的な YYYY.MM.DD 表記。桁が揃い一覧で読みやすい。
    return f"{dt.year}.{dt.month:02d}.{dt.day:02d}"


# 予定時刻をこれ以上過ぎても「予定」のままの記録は、元データの更新漏れと見なす。
# Launch Library は打ち上げ後に実績へ移すが、中止・無期限延期になった打ち上げは
# 予定のまま残り続ける。実際に 7/31 の Glonass-K1 が2週間「まもなく」として
# 打ち上げ一覧の先頭に居座っていた（2026-08-15 実測）。
# 毎日見る読者は、一度でも古い情報を見せられた時点で来なくなる。
LAUNCH_STALE_AFTER = timedelta(hours=6)


def countdown_label(iso: str | None, now: datetime, lang: str) -> str | None:
    dt = _parse_iso(iso)
    if dt is None:
        return None
    delta = dt - now
    secs = int(delta.total_seconds())
    if secs <= 0:
        # 予定時刻を過ぎた直後だけ「まもなく」。それ以降は表示しない
        # （過ぎた打ち上げに「まもなく」と出すのが最も信用を落とす）。
        if -secs <= LAUNCH_STALE_AFTER.total_seconds():
            return "T-0" if lang == "en" else "まもなく"
        return None
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


# 画像のない記事に使うイメージ写真。主題に応じて出し分ける。
# 元記事の写真ではないため、テンプレート側で「イメージ」と明示する。
_FALLBACK_BY_TOPIC = {
    "rocket": "fallback-launch.jpg",
    "moon": "fallback-launch.jpg",
    "mars": "fallback-research.jpg",
    "satellite": "fallback-space.jpg",
    "human": "fallback-space.jpg",
    "science": "fallback-research.jpg",
    "business": "fallback-space.jpg",
    "japan": "fallback-space.jpg",
}


def _fallback_image(topics: list[str]) -> str:
    for t in topics:
        if t in _FALLBACK_BY_TOPIC:
            return _FALLBACK_BY_TOPIC[t]
    return "fallback-space.jpg"


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
        it["published_short"] = fmt_date_short(it.get("published"), lang)
        # 自動翻訳で表示しているかどうか（UIバッジ用）
        it["is_translated"] = bool(
            it.get("lang") != lang and it.get(f"title_{lang}")
        )
        # 主題分類（原文で判定する。訳文よりキーワードが安定するため）
        it["topics"] = topics.classify(
            it.get("title", ""), it.get("summary", ""))
        # 一覧に出す主題ラベル（多すぎると読みにくいので1つに絞る）
        it["topic_labels"] = [topics.name(x, lang) for x in it["topics"][:1]]
        # サイト内の記事ページ。外部リンクに直接飛ばすと読者が離脱し、
        # 回遊も問い合わせも起きないため、必ず自サイトを経由させる。
        it["slug"] = news_slug(it)
        it["display_title"] = it.get(f"title_{lang}") or it.get("title") or ""
        it["display_summary"] = it.get(f"summary_{lang}") or it.get("summary") or ""
        # 本文は元記事の事実にもとづく独自解説（body_ja, 1000字以上）。
        # 切り詰めず全文を段落ごとに表示する。段落は空行区切りで分ける。
        body_ja = (it.get("body_ja") or "").strip()
        it["display_body"] = body_ja
        it["display_body_paras"] = _paragraphs(body_ja)
        # 画像のない記事にはトピックに応じたイメージ写真をあてる。
        # グレーの空欄が並ぶと一覧の見栄えが崩れ、記事も読まれにくくなるため。
        if not it.get("image"):
            it["stock_image"] = _fallback_image(it.get("topics", []))
            it["image_is_stock"] = True
        out.append(it)
    return out


# 打ち上げ結果の判定。実績側の status_name をそのまま日本語にせず、
# 「成功したのか否か」だけが一目で分かる3分類に落とす。
_RESULT_CLASS = {
    "success": "success",
    "launch successful": "success",
    "failure": "failure",
    "launch failure": "failure",
    "partial failure": "partial",
}


def prepare_launches(raw: list[dict], lang: str, now: datetime) -> list[dict]:
    """打ち上げを表示用に整形し、予定→実績の順に並べ直す。

    元データの `upcoming` をそのまま信じない。予定時刻を過ぎたまま
    更新されない記録が「まもなく」として先頭に残り続けるため、
    こちら側で時刻を見て判定する（LAUNCH_STALE_AFTER）。
    """
    # 「今日」の境目は読者のいる時間帯で切る。日本語サイトは日本時間、
    # 英語サイトは表示に合わせて UTC。
    tz = JST if lang == "ja" else timezone.utc
    today = now.astimezone(tz).date()
    out = []
    for it in raw:
        it = dict(it)
        dt = _parse_iso(it.get("net"))
        upcoming = bool(it.get("upcoming", True))
        # 予定時刻を大きく過ぎた「予定」は、こちらのデータが古いだけ。
        stale = bool(upcoming and dt is not None
                     and (now - dt) > LAUNCH_STALE_AFTER)
        if stale:
            upcoming = False
        it["upcoming"] = upcoming
        it["stale"] = stale
        # 日程が未確定の打ち上げは 00:00 UTC が「日付だけ決まっている」印として
        # 入ってくる。これを JST に直すと 09:00 という決まっていない時刻を
        # 断言してしまうので、時刻は出さず未定と明示する。
        time_tbd = bool(dt is not None and dt.hour == 0 and dt.minute == 0
                        and (it.get("status") or "").upper() in ("TBD", "TBC"))
        it["time_tbd"] = time_tbd
        it["net_display"] = fmt_date(it.get("net"), lang, with_time=not time_tbd)
        if time_tbd:
            it["net_display"] += f"　{_t('launches.time_tbd', lang)}"
        it["net_short"] = fmt_date_short(it.get("net"), lang)
        # カウントダウンは予定の打ち上げのみ。実績に「まもなく」と出さない。
        it["countdown"] = countdown_label(it.get("net"), now, lang) if upcoming else None
        if upcoming and time_tbd and dt is not None:
            # 時刻が決まっていないものを秒まで刻むと、無い精度を主張することになる。
            days = max((dt - now).days, 0)
            it["countdown"] = f"T-{days}日" if lang == "ja" else f"T-{days}d"
        st = (it.get("status_name") or it.get("status") or "").lower()
        it["status_class"] = _STATUS_CLASS.get(st, "tbd")
        it["result_class"] = _RESULT_CLASS.get(st) if not upcoming else None
        # 「今日」「今週」の仕分け。日本の読者が見るので日本時間で切る。
        if dt is not None:
            days = (dt.astimezone(tz).date() - today).days
            it["days_from_today"] = days
            it["is_today"] = days == 0
            it["is_this_week"] = 0 <= days <= 6
        else:
            it["days_from_today"] = None
            it["is_today"] = False
            it["is_this_week"] = False
        # 日本の打ち上げ。日本の宇宙開発に関わる人が最も追う対象なので、
        # 世界の予定に埋もれさせず別枠で出す（射場が海外でも運用者が日本なら含む）。
        it["is_japan"] = "JPN" in (it.get("country"), it.get("provider_country"))
        # 一覧の見出し分け。並び順と一致するので、切り替わった所に見出しを出す。
        if not upcoming:
            it["group"] = "results"
        elif it["is_today"]:
            it["group"] = "today"
        elif it["is_this_week"]:
            it["group"] = "this_week"
        else:
            it["group"] = "later"
        out.append(it)

    # 予定は近い順、実績は新しい順。stale を降格した結果を必ず並べ直す。
    upcoming_list = sorted([l for l in out if l["upcoming"]],
                           key=lambda x: x.get("net") or "")
    past_list = sorted([l for l in out if not l["upcoming"]],
                       key=lambda x: x.get("net") or "", reverse=True)
    return upcoming_list + past_list


def prepare_procurement(raw: list[dict], lang: str) -> list[dict]:
    """調達公告を表示用に整形する。

    日本の官公庁の公告なので日本語サイトにのみ出す。英語に機械翻訳すると
    案件名の正確さが失われ、応札の判断材料として使えなくなる。
    """
    if lang != "ja":
        return []
    today = datetime.now(JST).date()
    out = []
    for it in raw:
        it = dict(it)
        it["issued_display"] = fmt_date(it.get("issued"), lang)
        # 締切は公告PDFから抜いた実データ。取れなかったものは空のまま
        # （推測で埋めない）。まず知りたいのは「まだ間に合うか」。
        dl = it.get("deadline")
        it["deadline_display"] = None
        it["is_open"] = None
        it["days_left"] = None
        if dl:
            try:
                d = datetime.strptime(dl, "%Y-%m-%d").date()
            except ValueError:
                d = None
            if d:
                it["deadline_display"] = f"{d.year}年{d.month}月{d.day}日"
                it["days_left"] = (d - today).days
                it["is_open"] = it["days_left"] >= 0
        # 概要は案件名の再掲から始まることが多いので落とす
        desc = (it.get("description") or "").strip()
        name = (it.get("name") or "").strip()
        if name and desc.startswith(name):
            desc = desc[len(name):].lstrip("　 、。・-—")
        it["description"] = desc
        # 入札か随意契約かは応札を検討する側にとって決定的な差なので明示する。
        # 随意契約の公示は相手方が決まっており、参入の機会にはならない。
        body = name + " " + desc
        if "随意契約" in body:
            it["kind"] = "随意契約"
            it["kind_class"] = "tbd"
        elif "入札" in body or "公募" in body or "プロポーザル" in body:
            it["kind"] = "入札・公募"
            it["kind_class"] = "go"
        else:
            it["kind"] = ""
            it["kind_class"] = ""
        out.append(it)

    # 受付中を先に、締切が近い順。応札を検討する人が最初に知りたいのは
    # 「今から出せる案件はどれか」であって、公告された順ではない。
    def sort_key(p: dict) -> tuple:
        if p.get("is_open"):
            return (0, p.get("deadline") or "", "")
        return (1, "", _neg_str(p.get("issued") or ""))

    out.sort(key=sort_key)
    return out


# 本社所在地から地域を割り出すための対応表。都道府県だけを見る。
_AREA_DEFS = [
    ("hokkaido_tohoku", "北海道・東北",
     ("北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島")),
    ("kanto", "関東", ("茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川")),
    ("chubu", "中部", ("新潟", "富山", "石川", "福井", "山梨", "長野",
                       "岐阜", "静岡", "愛知")),
    ("kinki", "近畿", ("三重", "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山")),
    ("chugoku_shikoku", "中国・四国",
     ("鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知")),
    ("kyushu", "九州・沖縄", ("福岡", "佐賀", "長崎", "熊本", "大分",
                              "宮崎", "鹿児島", "沖縄")),
]


def company_area(hq: str | None) -> tuple[str, str] | None:
    """本社所在地から (地域ID, 地域名) を返す。判定できなければ None。"""
    hq = hq or ""
    for aid, name, prefs in _AREA_DEFS:
        if any(p in hq for p in prefs):
            return aid, name
    return None


def _company_areas(items: list[dict]) -> list[dict]:
    """絞り込みに出す地域。該当0件の地域は出さない。"""
    counts: dict[str, int] = {}
    for c in items:
        a = company_area(c.get("hq"))
        if a:
            counts[a[0]] = counts.get(a[0], 0) + 1
        c["area_id"], c["area_name"] = (a or ("", ""))
    return [{"id": aid, "name": name, "count": counts[aid]}
            for aid, name, _ in _AREA_DEFS if counts.get(aid)]


def _neg_str(s: str) -> str:
    """文字列の降順を昇順ソートの中で表すための反転キー。"""
    return "".join(chr(0x10FFFF - ord(c)) if ord(c) < 0x10FFFF else c for c in s)


def paper_slug(item: dict) -> str:
    """論文1件の安定したURLスラッグ。arXiv ID を使う。"""
    url = item.get("url") or item.get("pdf") or ""
    m = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", url)
    if m:
        return "arxiv-" + m.group(1).replace(".", "-")
    import hashlib
    return "paper-" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]


def prepare_papers(raw: list[dict], lang: str) -> list[dict]:
    out = []
    for it in raw:
        it = dict(it)
        it["published_display"] = fmt_date(it.get("published"), lang)
        it["published_short"] = fmt_date_short(it.get("published"), lang)
        it["slug"] = paper_slug(it)
        # 一覧・詳細で外部へ直接飛ばさず、自サイトの詳細ページへ誘導する
        it["detail_href"] = it["slug"]
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
            # hero がファイル名だけならサイト内の画像として解決する
            "hero_is_local": bool(meta.get("hero")) and not meta.get("hero", "").startswith("http"),
            "date": meta.get("date", ""),
            "date_display": fmt_date(meta.get("date"), lang) if meta.get("date") else "",
            # front matter の updated（YYYY-MM-DD）。加筆したらここを進める。
            # 無いと構造化データの dateModified が公開日のまま固定され、
            # 中身を直しても「更新されていない記事」として扱われる。
            "updated": meta.get("updated", ""),
            "updated_display": (
                fmt_date(meta.get("updated"), lang) if meta.get("updated") else ""
            ),
            "order": int(meta.get("order", "100") or "100"),
            "html": html,
        })
    articles.sort(key=lambda a: (a["order"], a["date"]), reverse=False)
    return articles


def load_faq(lang: str) -> tuple[dict, list[dict]]:
    """content/faq.<lang>.md を読む。 "Q: ..." / "A: ..." の対を抽出する。"""
    path = config.CONTENT_DIR / f"faq.{lang}.md"
    if not path.exists():
        return {}, []
    meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    faqs, q = [], None
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("Q:"):
            q = line[2:].strip()
        elif line.startswith("A:") and q:
            faqs.append({"q": q, "a": line[2:].strip()})
            q = None
    return meta, faqs


# 集約ページで表示する要約の上限。
# 下限だけ決めて上限を決めなかった結果、元記事をほぼ全訳した
# 1,000字前後の文章が並び、要約ではなく転載に近い状態になっていた。
# 引用は必要最小限にとどめ、続きは元記事で読んでもらう。
NEWS_SUMMARY_MAX = 300


def _paragraphs(text: str) -> list[str]:
    """本文を段落のリストにする。

    空行（\\n\\n）区切りがあればそれを尊重する。
    区切りが無い一塊の本文（旧データはこの形）は、句点で文に割り、
    3文ごとにまとめて読みやすい段落にする。
    """
    text = (text or "").strip()
    if not text:
        return []
    blocks = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(blocks) > 1:
        return blocks
    # 一塊の本文を句点で文に分け、3文ずつまとめる
    sentences = [s for s in re.split(r"(?<=。)", text) if s.strip()]
    if len(sentences) <= 3:
        return [text]
    paras, buf = [], ""
    for i, s in enumerate(sentences, 1):
        buf += s
        if i % 3 == 0:
            paras.append(buf.strip()); buf = ""
    if buf.strip():
        paras.append(buf.strip())
    return paras


def shorten_summary(text: str, limit: int = NEWS_SUMMARY_MAX) -> str:
    """要約を指定字数までに切り詰める。

    文の途中で切ると意味が壊れるため、句点を探して手前で切る。
    """
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    head = text[:limit]
    cut = max(head.rfind("。"), head.rfind("\n"))
    if cut >= limit // 2:          # 極端に短くならない位置に句点があれば使う
        return head[:cut + 1].strip()
    return head.rstrip() + "…"


def article_plain_text(html: str) -> str:
    """記事HTMLから素のテキストを取り出す（llms-full.txt 用）。"""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_mod.unescape(text)
    return re.sub(r"[ \t]+", " ", text).strip()


def news_slug(item: dict) -> str:
    """ニュース1件の安定したURLスラッグ。

    元記事URLのハッシュを使う。タイトルは翻訳で変わりうるが
    URLは変わらないため、再ビルドしてもスラッグが安定する。
    """
    import hashlib
    src = item.get("source_id") or "news"
    h = hashlib.sha1((item.get("url") or "").encode("utf-8")).hexdigest()[:10]
    return f"{src}-{h}"


# ヒーローのメインに向かない記事の特徴。
# 口語的な見出し、スポーツ・エンタメ寄りの話題、株価の値動きなど、
# 製造業向けB2Bメディアの「顔」として弱いものを後ろに回す。
_WEAK_TITLE = [
    "…", "!?", "！？", "ずりずり", "やばい", "すごい", "だった件", "してみた",
    "アニメ", "映画", "ドラマ", "ゲーム", "グッズ", "回顧", "振り返",
    "株価", "急落", "暴落", "ランキング",
]
# 逆に主役に据えたい主題（産業・技術・国内）
_STRONG_TOPIC = ("rocket", "satellite", "japan", "business")


# 訳文が崩れている見出しの兆候。金額や単位が原文のまま残ると起きやすい。
_BROKEN_TITLE = re.compile(
    r"[\$＄]\s*[\d.]+|(?i:\b(?:million|billion)\b)"
    r"|[A-Za-z]{4,}\s+[A-Za-z]{4,}\s+[A-Za-z]{4,}")


def _looks_broken_title(title: str) -> bool:
    return bool(_BROKEN_TITLE.search(title or ""))


def _featured_score(item: dict) -> int:
    """ヒーローのメイン適性を点数化する。高いほど主役向き。"""
    title = (item.get("display_title") or item.get("title") or "")
    score = 0
    if any(w in title for w in _WEAK_TITLE):
        score -= 5
    # 機械翻訳が崩れた見出しは、サイトで最も目立つ位置に出さない。
    # 「$ 7.1百万賞を受賞」がトップの主役になっていた実例がある。
    if item.get("title_ja_broken") or _looks_broken_title(title):
        score -= 20
    if len(title) < 14:            # 短すぎる見出しは大きく出すと間が持たない
        score -= 2
    for t in item.get("topics", []):
        if t in _STRONG_TOPIC:
            score += 2
    if item.get("lang") == "ja":   # 日本語ソースは訳のぎこちなさがない
        score += 2
    if item.get("body_ja"):        # 本文要約があるページは読み応えがある
        score += 3
    return score


def _order_featured(items: list[dict]) -> list[dict]:
    """新しさを保ちつつ、主役に向くものを先頭へ寄せる。

    直近の記事だけを対象に並べ替える。全体を点数順にすると
    古い記事が主役になり、媒体が更新されていないように見えるため。
    """
    head = items[:12]
    rest = items[12:]
    head.sort(key=lambda x: -_featured_score(x))
    return head + rest


# --- ページ分割 ---------------------------------------------------------
def _paginate(items: list, size: int) -> list[list]:
    """items を size 件ずつに分割する。空でも1ページは返す（空表示のため）。"""
    if not items:
        return [[]]
    return [items[i:i + size] for i in range(0, len(items), size)]


def _pagination_ctx(current: int, total: int) -> dict:
    """テンプレートに渡すページャ情報。リンクは現在ページからの相対パス。

    1ページ目は <base>/、2ページ目以降は <base>/<n>/ に出力される。
    したがって base のセグメント数に関係なく、
    1ページ目から見た n ページ目は "n/"、2ページ目以降から見た 1 ページ目は "../"。
    """
    if total <= 1:
        return {"total": 1}

    up = "" if current == 1 else "../"

    def href(p: int) -> str:
        return up if p == 1 else f"{up}{p}/"

    # 表示するページ番号（現在の前後2つ＋先頭・末尾）
    window = {1, total, current}
    for d in (-2, -1, 1, 2):
        if 1 <= current + d <= total:
            window.add(current + d)
    nums = sorted(window)
    entries = []
    prev = 0
    for n in nums:
        if prev and n - prev > 1:
            entries.append({"gap": True})
        entries.append({"num": n, "href": href(n), "current": n == current})
        prev = n
    return {
        "total": total, "current": current, "entries": entries,
        "prev": href(current - 1) if current > 1 else None,
        "next": href(current + 1) if current < total else None,
    }


# --- レンダリング -------------------------------------------------------
class Builder:
    @staticmethod
    def _asset_version() -> str:
        """CSS/JSの内容から短いハッシュを作る。

        ブラウザはCSSを長期キャッシュするため、更新してもURLが同じだと
        古いCSSが使われ続ける。内容が変わったときだけURLが変わるようにする。
        """
        import hashlib
        h = hashlib.sha256()
        for name in ("css/style.css", "js/main.js", "js/search.js", "js/contact-form.js"):
            p = config.STATIC_DIR / name
            if p.exists():
                h.update(p.read_bytes())
        return h.hexdigest()[:8]

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(config.TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True, lstrip_blocks=True,
        )
        self.now = datetime.now(timezone.utc)
        self.build_time = self.now.strftime("%Y-%m-%d %H:%M UTC")
        self.asset_ver = self._asset_version()
        self.year = self.now.year
        self.base_url = os.environ.get("SITE_BASE_URL", config.SITE_BASE_URL).rstrip("/")
        self.news_raw = _load_json("news.json").get("items", [])
        self.launches_raw = _load_json("launches.json").get("items", [])
        self.papers_raw = _load_json("papers.json").get("items", [])
        self.procurement_raw = _load_json("procurement.json").get("items", [])
        # 言語ごとに実際に出力したパスを記録（sitemap生成に使う）
        self.paths_by_lang: dict[str, list[str]] = {l: [] for l in config.LANGS}
        # sitemap の lastmod。内容が固定のページは公開日を入れる。
        # 全URLに毎日ビルド日を入れると更新シグナルとして無効になるため。
        self.lastmod_by_lang: dict[str, dict[str, str]] = {l: {} for l in config.LANGS}

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
            "asset_ver": self.asset_ver,
            "ga_id": config.GA_MEASUREMENT_ID,
            # 集約ページ（/a/）はインデックスさせない
            "noindex": path.startswith("a/"),
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

    def _source_chips(self, lang: str, up: int, current: str | None,
                      available: set[str] | None = None) -> list[dict]:
        """ニュースのソース別絞り込みチップ。

        up はそのページから news/ まで戻る階層数。
        ページ分割後も絞り込みが機能するよう、実ページへのリンクとして出す。

        available には「実際にページが生成されるソース」を渡す。
        ニュースは直近600件で入れ替わるため、設定に載っていても記事が1件も
        残っていないソースがある。そこへリンクすると 404 になり、
        実際に NASA・ESA・SpaceNews など8ソースが常時リンク切れだった。
        """
        back = "../" * up
        chips = [{"id": None, "name": _t("news.filter_all", lang),
                  "href": back or "./", "current": current is None}]
        for s in config.NEWS_SOURCES:
            if lang == "en" and s["lang"] != "en":
                continue
            if available is not None and s["id"] not in available:
                continue
            chips.append({"id": s["id"], "name": s["name"],
                          "href": f"{back}source/{s['id']}/",
                          "current": current == s["id"]})
        return chips

    def _write(self, lang: str, path: str, html: str) -> None:
        out_dir = self._lang_root(lang) / path
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html, encoding="utf-8")

        # noindex のページを sitemap に載せると矛盾したシグナルになる。
        # さらに薄いページが sitemap の大半を占めると、
        # クロールバジェットが自作記事に回らなくなる。
        # sitemap には「インデックスさせたいページだけ」を載せる。
        if not path.startswith("a/"):
            self.paths_by_lang[lang].append(path.rstrip("/") + "/")

    def _write_root(self, lang: str, html: str) -> None:
        out_dir = self._lang_root(lang)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html, encoding="utf-8")
        self.paths_by_lang[lang].append("")

    def _today_board(self, lang: str, launches: list[dict],
                     news: list[dict]) -> dict:
        """「今日の宇宙」ブロックの材料。

        毎日見る理由になるのは、毎日変わり・時刻という締切があり・
        当事者が実際に確認する情報だけ。この媒体でそれに当たるのは打ち上げ。
        次のT-0、今日と今週の本数、24時間以内の結果、今日のニュース本数を
        1画面にまとめ、「今日ここに来れば分かる」状態を作る。
        """
        tz = JST if lang == "ja" else timezone.utc
        today = self.now.astimezone(tz).date()
        upcoming = [l for l in launches if l.get("upcoming")]
        past = [l for l in launches if not l.get("upcoming")]

        # 直近24時間に完了した打ち上げ。結果が分かっているものだけ出す
        # （status が Go のまま止まっている記録を「結果」と偽らない）。
        since = self.now - timedelta(hours=24)
        results = []
        for l in past:
            dt = _parse_iso(l.get("net"))
            if dt is None or dt < since or dt > self.now:
                continue
            if not l.get("result_class"):
                continue
            results.append(l)
        results.sort(key=lambda x: x.get("net") or "", reverse=True)

        # 24時間以内に完了した打ち上げが無い日もある（実際そちらが多い）。
        # 空欄のまま出すと「動いていない媒体」に見えるので、
        # そのときは直近の完了分に切り替える。ラベルも変えて偽らない。
        recent_fallback = []
        if not results:
            recent_fallback = [l for l in past if l.get("result_class")][:3]

        # 「今日」ではなく直近24時間で数える。収集は1日1回なので、
        # 日付が変わった直後は「今日 0件」になり、止まった媒体に見えるため。
        news_recent = 0
        for n in news:
            dt = _parse_iso(n.get("published"))
            if dt is not None and since <= dt <= self.now:
                news_recent += 1

        # 「次の」打ち上げは、まだ時刻が来ていないものを指す。
        # 予定時刻を過ぎた（保留中かもしれない）ものを先頭に据えると、
        # 次に何があるのかという肝心の問いに答えられない。
        nxt = next((l for l in upcoming
                    if (_parse_iso(l.get("net")) or self.now) > self.now), None)

        return {
            "next": nxt or (upcoming[0] if upcoming else None),
            "today_launches": [l for l in upcoming if l.get("is_today")],
            "week_count": sum(1 for l in upcoming if l.get("is_this_week")),
            "results": results,
            "recent_results": recent_fallback,
            "news_count": news_recent,
            "date_display": fmt_date(self.now.isoformat(), lang),
        }

    def build_lang(self, lang: str) -> None:
        news = prepare_news(self.news_raw, lang)
        launches = prepare_launches(self.launches_raw, lang, self.now)
        papers = prepare_papers(self.papers_raw, lang)
        procurement = prepare_procurement(self.procurement_raw, lang)
        articles = load_articles(lang)
        home_label = _t("nav.home", lang)

        # 内容が変わらないページの lastmod。論文は公開日、記事は更新日。
        lm = self.lastmod_by_lang[lang]
        for p in papers:
            if p.get("published"):
                lm[f"p/{p['slug']}/"] = str(p["published"])[:10]
        for a in articles:
            d = a.get("updated") or a.get("date")
            if d:
                lm[f"articles/{a['slug']}/"] = str(d)[:10]

        # トップ（depth: ja=0, en=1 だが rel は言語ルート基準なので 0）
        ctx = self._ctx(lang, depth=0, active="home", path="")
        # 注目5本は本数を固定する。読者に「これで主要な動きは押さえた」
        # という完了感を与えるため（可変だと読み終わりの判断ができない）。
        # ヒーローは画像がある記事だけを使う。
        # 画像なしだとグレーの矩形が出て、トップの見栄えが崩れるため。
        with_img = [n for n in news if n.get("image")]
        # メインの1本は「媒体の顔」になるので、新しい順に置くだけにしない。
        # 製造業читатель向けB2Bメディアとして相応しいものを選ぶ。
        featured = _order_featured(with_img)[:5]
        used = {id(n) for n in featured}
        latest = [n for n in news if id(n) not in used][:12]
        upcoming = [l for l in launches if l.get("upcoming")]
        today_board = self._today_board(lang, launches, news)
        tcounts = topics.counts(news)
        topic_nav = [
            {"id": t["id"], "name": topics.name(t["id"], lang),
             "desc": topics.desc(t["id"], lang), "count": tcounts.get(t["id"], 0)}
            for t in topics.TOPICS if tcounts.get(t["id"], 0) >= 3
        ]
        topic_nav.sort(key=lambda x: -x["count"])
        # 独自資産（企業DB・参入ガイド）をトップに出す。
        # 集約ニュースより先に置かないと、差別化要素が読者に伝わらない。
        all_comp = companies.all_companies(lang)
        ctx.update(news=news, launches=launches, papers=papers, articles=articles,
                   featured=featured, latest=latest,
                   next_launches=upcoming[:3], today=today_board, topic_nav=topic_nav,
                   procurement=procurement[:5],
                   company_cats=companies.categories(lang),
                   featured_companies=all_comp[:14],
                   guides=[a for a in articles
                           if a.get("tag") in ("参入ガイド", "Entry Guide")][:6])
        ctx["jsonld"] = seo.build_jsonld(
            self.base_url, lang, "home",
            trail=[(home_label, self._url_for(lang, ""))])
        self._write_root(lang, self.env.get_template("home.html").render(**ctx))

        # ソース別ページを持つソース。絞り込みチップのリンク先に使う。
        # 実ページの生成と同じ集計を使い、リンクと実体をずらさない。
        by_source: dict[str, list[dict]] = {}
        for n in news:
            by_source.setdefault(n.get("source_id", "other"), []).append(n)
        live_sources = set(by_source)

        # 一覧ページ（言語ルートから1階層 → rel="../"）
        # 件数が多いものはページ分割する。1ページ目は news/、2ページ目以降は news/2/。
        paged = [
            ("news/", "news.html", "news", "news", news),
            ("launches/", "launches.html", "launches", "launches", launches),
            ("papers/", "papers.html", "papers", "papers", papers),
            ("articles/", "articles.html", "articles", "articles", articles),
        ]
        # 調達情報は日本語サイトのみ（日本の官公庁の公告のため）
        if procurement:
            paged.append(("procurement/", "procurement.html",
                          "procurement", "procurement", procurement))
        total_pages_built = 0
        for base_path, tpl, active, var, all_items in paged:
            chunks = _paginate(all_items, config.PAGE_SIZE)
            for pno, chunk in enumerate(chunks, 1):
                path = base_path if pno == 1 else f"{base_path}{pno}/"
                depth = 1 if pno == 1 else 2
                ctx = self._ctx(lang, depth=depth, active=active, path=path)
                ctx[var] = chunk
                ctx["pagination"] = _pagination_ctx(pno, len(chunks))
                # 日本の打ち上げは1ページ目に別枠で出す（件数が少なく埋もれるため）
                # 公告を見た人が次に要るのは「どうやって入るのか」。
                # 参入ガイドは検索から見つけてもらえていないので、
                # 文脈の合うこのページから確実に渡す。
                if active == "procurement":
                    want = ("space-procurement-jaxa", "manufacturing-entry-guide",
                            "space-quality-requirements")
                    by_slug = {a["slug"]: a for a in articles}
                    ctx["guides"] = [by_slug[s] for s in want if s in by_slug]
                if active == "launches" and pno == 1:
                    ctx["jp_launches"] = [
                        l for l in all_items
                        if l.get("upcoming") and l.get("is_japan")][:4]
                if active == "news":
                    ctx["source_chips"] = self._source_chips(
                        lang, up=depth - 1, current=None, available=live_sources)
                ctx["jsonld"] = seo.build_jsonld(
                    self.base_url, lang, active,
                    trail=[(home_label, self._url_for(lang, "")),
                           (_t(f"nav.{active}", lang), self._url_for(lang, base_path))],
                    news=chunk if active == "news" else None,
                    launches=chunk if active == "launches" else None,
                    papers=chunk if active == "papers" else None,
                    articles=chunk if active == "articles" else None)
                self._write(lang, path.rstrip("/"),
                            self.env.get_template(tpl).render(**ctx))
                total_pages_built += 1

        # 記事詳細（articles/<slug>/ → depth 2）
        for a in articles:
            path = f"articles/{a['slug']}/"
            page_url = self._url_for(lang, path)
            ctx = self._ctx(lang, depth=2, active="articles", path=path,
                            page_description=a.get("excerpt", ""))
            ctx["article"] = a
            # 構造化データで本文長を示すため、素の本文を渡す
            a.setdefault("plain_text", article_plain_text(a.get("html", "")))
            ctx["jsonld"] = seo.build_jsonld(
                self.base_url, lang, "article", article=a, page_url=page_url,
                trail=[(home_label, self._url_for(lang, "")),
                       (_t("nav.articles", lang), self._url_for(lang, "articles/")),
                       (a["title"], page_url)])
            html = self.env.get_template("article.html").render(**ctx)
            self._write(lang, f"articles/{a['slug']}", html)

        # ソース別ニュースページ（news/source/<id>/）
        # ページ分割によりチップの絞り込みが現在ページ内に限定されてしまうため、
        # ソースごとに実ページを持たせる。検索インデックス上も有利。
        source_pages = 0
        for sid, items in by_source.items():
            src_name = next((s["name"] for s in config.NEWS_SOURCES if s["id"] == sid), sid)
            base_path = f"news/source/{sid}/"
            chunks = _paginate(items, config.PAGE_SIZE)
            for pno, chunk in enumerate(chunks, 1):
                path = base_path if pno == 1 else f"{base_path}{pno}/"
                depth = 3 if pno == 1 else 4
                ctx = self._ctx(lang, depth=depth, active="news", path=path,
                                page_description=f"{src_name} — {_t('news.subtitle', lang)}")
                ctx["news"] = chunk
                ctx["pagination"] = _pagination_ctx(pno, len(chunks))
                ctx["source_chips"] = self._source_chips(
                    lang, up=depth - 1, current=sid, available=live_sources)
                ctx["source_name"] = src_name
                ctx["jsonld"] = seo.build_jsonld(
                    self.base_url, lang, "news",
                    trail=[(home_label, self._url_for(lang, "")),
                           (_t("nav.news", lang), self._url_for(lang, "news/")),
                           (src_name, self._url_for(lang, base_path))],
                    news=chunk)
                self._write(lang, path.rstrip("/"),
                            self.env.get_template("news.html").render(**ctx))
                source_pages += 1
        total_pages_built += source_pages

        # FAQページ（FAQPage構造化データ付き＝AI検索に最も引用されやすい形式）
        faq_meta, faqs = load_faq(lang)
        if faqs:
            ctx = self._ctx(lang, depth=1, active="faq", path="faq/",
                            page_description=faq_meta.get("excerpt", ""))
            ctx["faqs"] = faqs
            ctx["faq_title"] = faq_meta.get("title", _t("faq.title", lang))
            ctx["faq_excerpt"] = faq_meta.get("excerpt", "")
            ctx["jsonld"] = seo.build_jsonld(
                self.base_url, lang, "faq", faqs=faqs,
                trail=[(home_label, self._url_for(lang, "")),
                       (_t("nav.faq", lang), self._url_for(lang, "faq/"))])
            self._write(lang, "faq", self.env.get_template("faq.html").render(**ctx))

        # サイト内検索ページ＋検索インデックス（サーバー不要）
        ctx = self._ctx(lang, depth=1, active="search", path="search/",
                        page_description=_t("search.subtitle", lang))
        ctx["jsonld"] = seo.build_jsonld(
            self.base_url, lang, "search",
            trail=[(home_label, self._url_for(lang, "")),
                   (_t("nav.search", lang), self._url_for(lang, "search/"))])
        self._write(lang, "search", self.env.get_template("search.html").render(**ctx))
        config.STATIC_DIR.mkdir(parents=True, exist_ok=True)
        (config.STATIC_DIR / f"search-{lang}.json").write_text(
            seo.build_search_index(lang, news, papers, launches, articles),
            encoding="utf-8")

        # トピック別ページ（topics/<id>/）
        # 時系列一覧だけでは読者が関心領域にたどり着けないため、
        # 主題ごとの入口を実ページとして持たせる。
        topic_pages = 0
        for tp in topics.TOPICS:
            items = [n for n in news if tp["id"] in n.get("topics", [])]
            if len(items) < 3:
                continue
            base_path = f"topics/{tp['id']}/"
            chunks = _paginate(items, config.PAGE_SIZE)
            for pno, chunk in enumerate(chunks, 1):
                path = base_path if pno == 1 else f"{base_path}{pno}/"
                depth = 2 if pno == 1 else 3
                ctx = self._ctx(lang, depth=depth, active="topics", path=path,
                                page_description=topics.desc(tp["id"], lang))
                ctx["news"] = chunk
                ctx["pagination"] = _pagination_ctx(pno, len(chunks))
                ctx["topic_name"] = topics.name(tp["id"], lang)
                ctx["topic_desc"] = topics.desc(tp["id"], lang)
                ctx["topic_id"] = tp["id"]
                ctx["all_topics"] = [
                    {"id": x["id"], "name": topics.name(x["id"], lang),
                     "href": f"{'../' * (depth - 1)}{x['id']}/",
                     "current": x["id"] == tp["id"]}
                    for x in topics.TOPICS
                    if sum(1 for n in news if x["id"] in n.get("topics", [])) >= 3
                ]
                ctx["jsonld"] = seo.build_jsonld(
                    self.base_url, lang, "news",
                    trail=[(home_label, self._url_for(lang, "")),
                           (topics.name(tp["id"], lang), self._url_for(lang, base_path))],
                    news=chunk)
                self._write(lang, path.rstrip("/"),
                            self.env.get_template("topic.html").render(**ctx))
                topic_pages += 1
        total_pages_built += topic_pages

        # ニュース詳細ページ（a/<slug>/）
        # 一覧から直接外部サイトへ飛ばすと、読者が即座に離脱して
        # 回遊も問い合わせも起きない。必ず自サイトのページを経由させ、
        # 関連記事と企業DBへの導線をそこで提示する。
        by_topic: dict[str, list[dict]] = {}
        for n in news:
            for tid in n.get("topics", []):
                by_topic.setdefault(tid, []).append(n)

        for n in news:
            # 同じ主題の記事を関連として出す（自分自身は除く）
            rel_items: list[dict] = []
            seen_slugs = {n["slug"]}
            for tid in n.get("topics", []):
                for cand in by_topic.get(tid, []):
                    if cand["slug"] in seen_slugs:
                        continue
                    seen_slugs.add(cand["slug"])
                    rel_items.append(cand)
                    if len(rel_items) >= 6:
                        break
                if len(rel_items) >= 6:
                    break

            path = f"a/{n['slug']}/"
            ctx = self._ctx(lang, depth=2, active="news", path=path,
                            page_description=(n.get("display_summary") or "")[:150])
            ctx["item"] = n
            ctx["related"] = rel_items
            ctx["jsonld"] = seo.build_jsonld(
                self.base_url, lang, "news",
                trail=[(home_label, self._url_for(lang, "")),
                       (_t("nav.news", lang), self._url_for(lang, "news/")),
                       (n["display_title"][:60], self._url_for(lang, path))],
                news=[n])
            self._write(lang, path.rstrip("/"),
                        self.env.get_template("news_detail.html").render(**ctx))
        total_pages_built += len(news)

        # 論文詳細ページ（p/<slug>/）
        # 一覧から arXiv へ直接飛ばさず、自サイトの詳細ページを経由させる。
        # 概要は引用の範囲にとどめ、全文は出典（arXiv）で読んでもらう。
        by_cat: dict[str, list[dict]] = {}
        for p in papers:
            for c in p.get("categories", []):
                by_cat.setdefault(c, []).append(p)
        for p in papers:
            rel_items: list[dict] = []
            seen = {p["slug"]}
            for c in p.get("categories", []):
                for cand in by_cat.get(c, []):
                    if cand["slug"] in seen:
                        continue
                    seen.add(cand["slug"])
                    rel_items.append(cand)
                    if len(rel_items) >= 6:
                        break
                if len(rel_items) >= 6:
                    break
            path = f"p/{p['slug']}/"
            ctx = self._ctx(lang, depth=2, active="papers", path=path,
                            page_description=(p.get("summary") or "")[:150])
            ctx["item"] = p
            ctx["related"] = rel_items
            # <title> だけ丸める。h1 は原題の全文のまま
            ctx["head_title"] = head_title(p.get("title") or "")
            # 一覧と同じ "papers"（ItemList）を個別ページにも出していたため、
            # ページ単体では記事型の構造化データが1つも無かった（2026-08-05 修正）。
            ctx["jsonld"] = seo.build_jsonld(
                self.base_url, lang, "paper",
                trail=[(home_label, self._url_for(lang, "")),
                       (_t("nav.papers", lang), self._url_for(lang, "papers/")),
                       (p["title"][:60], self._url_for(lang, path))],
                paper=p, page_url=self._url_for(lang, path))
            self._write(lang, path.rstrip("/"),
                        self.env.get_template("paper_detail.html").render(**ctx))
        total_pages_built += len(papers)

        # 企業DBページ（このサイト唯一の独自資産。集約でないためSEO評価が付く）
        comp_cats = companies.categories(lang)
        for cat in [None] + comp_cats:
            cid = cat["id"] if cat else None
            path = "companies/" if cid is None else f"companies/{cid}/"
            depth = 1 if cid is None else 2
            ctx = self._ctx(lang, depth=depth, active="companies", path=path,
                            page_description=_t("companies.subtitle", lang))
            ctx["companies"] = (companies.all_companies(lang) if cid is None
                                else companies.by_category(cid, lang))
            ctx["cats"] = [
                {**c, "href": f"{'../' * (depth - 1)}{c['id']}/"} for c in comp_cats
            ]
            ctx["current_cat"] = cid
            ctx["back_to_all"] = "../" if cid else "./"
            # 地域での絞り込み。サプライヤーを探す側は「近さ」で候補を絞る。
            # 本社所在地から機械的に作るので、事実以上のことを言わない。
            ctx["areas"] = _company_areas(ctx["companies"])
            ctx["disclaimer"] = companies.disclaimer(lang)
            ctx["jsonld"] = seo.build_jsonld(
                self.base_url, lang, "companies",
                trail=[(home_label, self._url_for(lang, "")),
                       (_t("companies.title", lang), self._url_for(lang, "companies/"))])
            self._write(lang, path.rstrip("/"),
                        self.env.get_template("companies.html").render(**ctx))
            total_pages_built += 1

        # 問い合わせ・広告ページ（収益導線。受け皿がなければ成果はゼロになる）
        ctx = self._ctx(lang, depth=1, active="contact", path="contact/",
                        page_description=_t("contact.subtitle", lang))
        ctx["contact_kinds"] = business.contact_kinds(lang)
        ctx["contact_email"] = config.CONTACT_EMAIL
        ctx["google_form_url"] = config.GOOGLE_FORM_URL
        ctx["google_form_height"] = config.GOOGLE_FORM_HEIGHT
        ctx["form_kinds"] = [k["label"] for k in business.contact_kinds(lang)]
        ctx["form_endpoint"] = config.FORM_ENDPOINT
        ctx["form_access_key"] = ""
        ctx["company_name"] = config.COMPANY_NAME
        ctx["company_url"] = config.COMPANY_URL
        ctx["jsonld"] = seo.build_jsonld(
            self.base_url, lang, "contact",
            trail=[(home_label, self._url_for(lang, "")),
                   (_t("contact.title", lang), self._url_for(lang, "contact/"))])
        self._write(lang, "contact", self.env.get_template("contact.html").render(**ctx))

        ctx = self._ctx(lang, depth=1, active="advertise", path="advertise/",
                        page_description=_t("ad.subtitle", lang))
        ctx["ad_audience"] = business.AD_AUDIENCE.get(lang, business.AD_AUDIENCE["ja"])
        ctx["ad_menu"] = business.AD_MENU.get(lang, business.AD_MENU["ja"])
        ctx["ad_mailto"] = business.ad_mailto()
        ctx["ad_stats"] = [
            {"n": companies.count(), "label": _t("nav.companies", lang)},
            {"n": len(news), "label": _t("nav.news", lang)},
            {"n": len(launches), "label": _t("nav.launches", lang)},
            {"n": len(articles), "label": _t("nav.articles", lang)},
        ]
        ctx["jsonld"] = seo.build_jsonld(
            self.base_url, lang, "advertise",
            trail=[(home_label, self._url_for(lang, "")),
                   (_t("ad.title", lang), self._url_for(lang, "advertise/"))])
        self._write(lang, "advertise", self.env.get_template("advertise.html").render(**ctx))

        # 運営会社。誰が運営しているかを明示するページ。
        ctx = self._ctx(lang, depth=1, active="about", path="about/",
                        page_description=_t("about.subtitle", lang))
        ctx["about_why"] = business.ABOUT_WHY.get(lang, business.ABOUT_WHY["ja"])
        ctx["about_policy"] = business.EDITORIAL_POLICY.get(
            lang, business.EDITORIAL_POLICY["ja"])
        ctx["company_profile"] = config.COMPANY_PROFILE
        ctx["jsonld"] = seo.build_jsonld(
            self.base_url, lang, "about",
            trail=[(home_label, self._url_for(lang, "")),
                   (_t("about.title", lang), self._url_for(lang, "about/"))])
        self._write(lang, "about", self.env.get_template("about.html").render(**ctx))
        total_pages_built += 3

        # RSSフィード
        feed = seo.build_feed(self.base_url, lang, articles, news, self.now)
        feed_dir = self._lang_root(lang)
        feed_dir.mkdir(parents=True, exist_ok=True)
        (feed_dir / "feed.xml").write_text(feed, encoding="utf-8")

        # 打ち上げカレンダー（.ics）。
        # 毎日サイトを開かせるより、相手のカレンダーに予定を置いてもらう方が
        # 強い。打ち上げが近づくたびに向こうから戻ってくる導線になる。
        (feed_dir / "launches.ics").write_text(
            self._launch_ics(lang, launches), encoding="utf-8")

        print(f"  [{lang}] home + {total_pages_built} 一覧ページ "
              f"+ {len(articles)} articles + feed.xml + launches.ics")

    @staticmethod
    def _ics_escape(s: str) -> str:
        return (str(s or "").replace("\\", "\\\\").replace(";", r"\;")
                .replace(",", r"\,").replace("\n", r"\n"))

    def _launch_ics(self, lang: str, launches: list[dict]) -> str:
        """予定の打ち上げをカレンダー購読用の iCalendar にする。

        時刻未定（TBD）は分単位の精度が無いが、予定として押さえたい需要が
        あるので出す。確度は STATUS と本文で伝え、勝手に確定扱いしない。
        """
        def stamp(dt: datetime) -> str:
            return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        lines = [
            "BEGIN:VCALENDAR", "VERSION:2.0",
            "PRODID:-//UchUchU//Launch Schedule//" + lang.upper(),
            "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
            "X-WR-CALNAME:" + self._ics_escape(
                "UchUchU 打ち上げ予定" if lang == "ja" else "UchUchU Launch Schedule"),
            "X-WR-TIMEZONE:" + ("Asia/Tokyo" if lang == "ja" else "UTC"),
            # 購読側が再取得する間隔。日次更新なので12時間で足りる
            "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
            "X-PUBLISHED-TTL:PT12H",
        ]
        now_stamp = stamp(self.now)
        for l in launches:
            if not l.get("upcoming"):
                continue
            dt = _parse_iso(l.get("net"))
            if dt is None or not l.get("id"):
                continue
            desc = " / ".join(x for x in (
                l.get("provider"), l.get("rocket"), l.get("mission"),
                l.get("status_name")) if x)
            lines += [
                "BEGIN:VEVENT",
                f"UID:{l['id']}@uchuchu.tech",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART:{stamp(dt)}",
                f"DTEND:{stamp(dt + timedelta(hours=1))}",
                "SUMMARY:" + self._ics_escape(l.get("name")),
                "LOCATION:" + self._ics_escape(l.get("location")),
                "DESCRIPTION:" + self._ics_escape(desc),
                "URL:" + self._url_for(lang, "launches/"),
                # 予定は動く。確定扱いにせず TENTATIVE を明示する
                "STATUS:" + ("CONFIRMED" if l.get("status_class") == "go" else "TENTATIVE"),
                "END:VEVENT",
            ]
        lines.append("END:VCALENDAR")
        return "\r\n".join(lines) + "\r\n"

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

        # sitemap.xml（実際に生成したページのみ / lastmod + hreflang）
        articles_ja = load_articles(config.DEFAULT_LANG)
        (config.DIST_DIR / "sitemap.xml").write_text(
            seo.build_sitemap(self.base_url, self.paths_by_lang, self.now,
                              self.lastmod_by_lang),
            encoding="utf-8")

        # IndexNow の鍵ファイル。検索エンジンがこれを取得して
        # サイト所有者であることを確認する（Webmaster Toolsのログイン不要）。
        (config.DIST_DIR / indexnow.key_filename()).write_text(
            indexnow.KEY, encoding="utf-8")

        # Bing Webmaster Tools の所有者確認ファイル（2026-07-30 追加）。
        # Copilot / ChatGPT検索 は Bing のインデックスを使うため、Bing側の
        # 表示回数・クロール状況を計測できるようにしておく。
        # 確認後もこのファイルを消すと所有者確認が外れるので、ビルド出力に含め続ける。
        (config.DIST_DIR / "BingSiteAuth.xml").write_text(
            '<?xml version="1.0"?>\n<users>\n  <user>'
            "718C5ECC89904D3E06AE85EA7FBA31D6"
            "</user>\n</users>\n",
            encoding="utf-8",
        )

        # llms.txt（AI検索にサイト構造を伝える）
        articles_en = load_articles("en")
        (config.DIST_DIR / "llms.txt").write_text(
            seo.build_llms_txt(self.base_url, articles_ja, articles_en),
            encoding="utf-8")

        # llms-full.txt（自作コンテンツの全文をAIに提供。集約記事は著作権上含めない）
        for arts in (articles_ja, articles_en):
            for a in arts:
                a["plain"] = article_plain_text(a.get("html", ""))
        (config.DIST_DIR / "llms-full.txt").write_text(
            seo.build_llms_full(self.base_url, articles_ja, articles_en,
                                load_faq("ja")[1], load_faq("en")[1]),
            encoding="utf-8")

        # 404
        ctx = self._ctx(config.DEFAULT_LANG, depth=0, active="", path="404")
        four04 = self.env.from_string(_FOUR04_TPL).render(**ctx)
        (config.DIST_DIR / "404.html").write_text(four04, encoding="utf-8")
        extras = ("static/, .nojekyll, robots.txt, sitemap.xml, llms.txt, "
                  "llms-full.txt, 404.html, indexnow-key")
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
