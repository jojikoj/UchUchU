"""毎日のニュースから、製造業向けの解説記事を1本作って公開する。

## なぜこれを作るか

ニュースの集約ページは noindex にしたため、検索評価には一切寄与しない。
資産になるのはオリジナル記事だけで、それが12本では競合に届かない。

一方でニュースは1日約44件入ってくる。この中から製造業に意味のあるものを選び、
「部品を作る側にとって何を意味するか」を書けば、それは他社が書いていない
オリジナル記事になる。soraeも宙畑も宇宙業界向けに書いており、
受注側の目線では書いていない。ここが空いている。

## 全自動にあたっての方針

**量を出す仕組みだけ作って中身の判定を入れない、という失敗を繰り返さない。**
実際にこのサイトでは、集約ページ1,140本をインデックスさせていた事故と、
要約に上限を設けず元記事をほぼ全訳していた事故が起きている。
どちらも「下限だけ決めて上限を決めなかった」ことが原因だった。

したがってここでは、公開前に必ず次を機械で検査する。

1. **数字の捏造** — 記事中の数値が出典に存在するか（AIは数字を作る）
2. **AEO要件** — 表・冒頭の結論・まとめ・見出し数・文字数
3. **重複** — 既存記事と主題が重なっていないか

**基準を満たす候補が無い日は書かない。** プレイブックの唯一の基準は
「ネタが持つかどうか」で、尽きたら出さないと明記されている。
毎日1本を先に決めて中身を捻り出すのが、最も避けたい進め方になる。

    python3 tools/daily_article.py           # 通常実行
    python3 tools/daily_article.py --dry     # 生成するが公開しない
"""
from __future__ import annotations

import datetime
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from uchuchu import config                      # noqa: E402
from uchuchu.collectors import fulltext         # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "content" / "articles"
STATE = ROOT / "data" / "daily_article_state.json"
LOG_DIR = (pathlib.Path.home() / "claude_AIR/TOEcompany/コンテンツ部"
           / "案件/UchUchU/ログ")

# 記事生成に使うモデル。1日1回だけの呼び出しなので、
# バッチ処理と違い上位モデルを使ってよい（品質がそのまま資産になる）。
MODEL = "sonnet"

# 製造業にとっての関連度を測る語。多く含むほど記事にする価値が高い。
STRONG = ["部品", "製造", "量産", "サプライ", "調達", "素材", "材料",
          "加工", "工場", "受注", "契約", "装置", "生産", "供給"]
WEAK = ["開発", "実証", "試験", "打ち上げ", "衛星", "ロケット", "計画"]

# これ未満の点数しか取れない日は記事にしない
MIN_SCORE = 3
# 生成する記事の長さ
MIN_CHARS = 2000


# --- 候補の選定 ---------------------------------------------------------

def score(item: dict) -> int:
    text = " ".join(str(item.get(k) or "") for k in
                    ("title_ja", "title", "summary_ja", "body_ja"))
    s = sum(2 for w in STRONG if w in text)
    s += sum(1 for w in WEAK if w in text)
    return s


def pick(items: list[dict], used: set[str], top: int = 5) -> list[dict]:
    """まだ記事にしていない中から、製造業に関係する順に候補を返す。

    1件だけ返すと、その記事の本文が取得できなかった日に何も書けなくなる。
    出典を取れない媒体は一定数あるので、控えを持たせる。
    """
    today = datetime.date.today()
    cands = []
    for it in items:
        if it.get("url") in used:
            continue
        d = (it.get("published") or it.get("date") or "")[:10]
        if not re.match(r"\d{4}-\d\d-\d\d", d):
            continue
        # 3日以内のものだけ。古い話題を今日の記事にしない
        try:
            if (today - datetime.date.fromisoformat(d)).days > 3:
                continue
        except ValueError:
            continue
        sc = score(it)
        if sc >= MIN_SCORE:
            cands.append((sc, it))
    cands.sort(key=lambda x: -x[0])
    return [it for _, it in cands[:top]]


# --- 生成 ---------------------------------------------------------------

_PROMPT = """あなたは、日本の製造業に向けた宇宙産業メディアの編集者です。

以下のニュースを題材に、**製造業の読者に向けた解説記事**を書いてください。
ニュースの紹介記事ではありません。「この出来事は、部品や装置を作る企業に
とって何を意味するか」を解説する、独自の記事です。

## 絶対に守ること

- **数字は下の「使ってよい数値」に載っているものだけ**を使ってください。
  そこに無い金額・件数・規模・シェアは、**一切書かないこと**。
  市場規模や業界の相場を補足したくなっても、数字では書かず
  「大きい」「増えている」のように言葉で書いてください。
- 出典に無い企業名・製品名を、事実であるかのように書かない
- 推測を断定で書かない。「〜と考えられる」「〜の可能性がある」と明示する
- 元記事の翻訳をしない。事実の要点は簡潔に触れる程度に留める

## 構成（すべて必須）

1. 冒頭150〜250字で**結論を言い切る**。太字（**〜**）を1箇所使う
2. `## ` の見出しを4つ以上
3. **表を1つ以上**（比較・分類・整理のいずれか）。Markdownの表形式
4. 箇条書きを3つ以上
5. `## まとめ` を最後に置き、箇条書きで要点を5つ程度
6. 全体で2000字以上

## 書き方

- 常体（だ・である）で書く
- 見出しは問いの形にする（「〜とは何か」「何が変わるのか」）
- 煽り表現（衝撃・すぎる・もう終わり）を使わない
- 「いかがでしたか」のような字数稼ぎを書かない

## 内部リンク

本文中に、下の既存記事のうち**関連するもの2本へのリンク**を自然に入れてください。
形式は `[記事タイトル](/articles/スラッグ/)` です。
関連が薄いものを無理に張らないこと。

{related}

## 出力形式

1行目にタイトルのみを書き、2行目以降に本文を書いてください。
タイトルは問いの形か、「A — B」の形にする。40字以内。
front matter（---で囲む部分）は書かないでください。

---

使ってよい数値（これ以外の数字は書かない）:
{numbers}

ニュースの見出し: {title}
出典メディア: {source}

ニュース本文:
{body}
"""


def related_articles() -> str:
    """既存記事の一覧。生成した記事から内部リンクを張らせるために渡す。

    どこからもリンクされない記事は検索評価が伸びない。
    毎日increaseする記事が全部孤立すると、本数だけ増えて効果が出ない。
    """
    out = []
    for f in sorted(ARTICLES.glob("*.ja.md")):
        slug = f.name.replace(".ja.md", "")
        if slug.startswith("news-"):        # 解説記事同士は結びつけない
            continue
        m = re.search(r"title: (.+)", f.read_text(encoding="utf-8"))
        if m:
            out.append(f"- [{m.group(1).strip()}](/articles/{slug}/)")
    return "\n".join(out)


def allowed_numbers(source: str) -> str:
    """出典に出てくる数値を、日本語表記に直して一覧にする。

    「書くな」と禁止するより「これだけ使ってよい」と示すほうが守られる。
    実際、禁止するだけでは毎回それらしい数字が作られた。
    """
    out = []
    for m in re.finditer(
            r"[\$€£]?\s*([\d][\d,]*(?:\.\d+)?)\s*"
            r"(thousand|million|billion|trillion|%|percent)?", source, re.I):
        raw, unit = m.group(1), (m.group(2) or "").lower()
        try:
            v = float(raw.replace(",", ""))
        except ValueError:
            continue
        if unit in ("million", "billion", "trillion", "thousand"):
            man = v * {"thousand": 0.1, "million": 100,
                       "billion": 100_000, "trillion": 100_000_000}[unit]
            jp = (f"{man / 10_000:g}億" if man >= 10_000 else f"{man:g}万")
            out.append(f"{m.group(0).strip()} → {jp}")
        elif unit in ("%", "percent"):
            out.append(f"{raw}%")
        elif v >= 10:
            out.append(raw)
    # 重複を除き、多すぎても読めないので上限を設ける
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x); uniq.append(x)
    return "、".join(uniq[:25])


def generate(item: dict, body: str, retry_note: str = "") -> tuple[str, str] | None:
    prompt = retry_note + _PROMPT.format(
        title=item.get("title_ja") or item.get("title", ""),
        source=item.get("source_name") or item.get("source") or "",
        numbers=allowed_numbers(body) or "（出典に数値なし。数字を一切書かないこと）",
        related=related_articles(),
        body=body[:6000])
    try:
        p = subprocess.run(
            ["claude", "-p", "--model", MODEL, prompt],
            capture_output=True, text=True, timeout=600,
            stdin=subprocess.DEVNULL)
    except Exception as e:
        print(f"  生成に失敗: {type(e).__name__}: {e}")
        return None
    out = (p.stdout or "").strip()
    if not out or "\n" not in out:
        # 失敗の原因が分からないと再発時に手が出せないので、必ず記録する
        print(f"  生成が空: rc={p.returncode} out={len(out)}字 "
              f"err={(p.stderr or '')[:200]}")
        return None
    title, rest = out.split("\n", 1)
    return title.strip().lstrip("#").strip(), rest.strip()


# --- 検査 ---------------------------------------------------------------

def _values(text: str, ja: bool) -> set[float]:
    """文中の数値を、単位を掛けた実数の集合にして返す。

    出典は英語（$70 million）、記事は日本語（7000万ドル）になるため、
    文字列のまま比べても一致しない。実数に直してから突き合わせる。
    """
    scale_ja = {"": 1, "万": 1e4, "億": 1e8, "兆": 1e12}
    scale_en = {"": 1, "thousand": 1e3, "million": 1e6,
                "billion": 1e9, "trillion": 1e12}
    out: set[float] = set()
    pat = (r"([\d][\d,]*(?:\.\d+)?)\s*(万|億|兆)?" if ja else
           r"([\d][\d,]*(?:\.\d+)?)\s*(thousand|million|billion|trillion)?")
    for m in re.finditer(pat, text, flags=0 if ja else re.I):
        try:
            v = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        unit = (m.group(2) or "").lower()
        out.add(v * (scale_ja if ja else scale_en).get(unit, 1))
    return out


def check_numbers(article: str, source: str) -> list[str]:
    """記事中の数値のうち、出典に見当たらないものを返す。

    AIは数字を作る。ここが最も事故になりやすいので機械で潰す。
    年号と、単位を伴わない一桁の数は対象から外す（誤検出が多いため）。
    """
    src = _values(source, ja=False) | _values(source, ja=True)
    bad = []
    for m in re.finditer(r"([\d][\d,]*(?:\.\d+)?)\s*(万|億|兆|%|％)?", article):
        raw, unit = m.group(1), m.group(2) or ""
        try:
            v = float(raw.replace(",", ""))
        except ValueError:
            continue
        if unit in ("万", "億", "兆"):
            v *= {"万": 1e4, "億": 1e8, "兆": 1e12}[unit]
        # 西暦は本文の文脈で使われるので対象外
        if 1900 <= v <= 2100 and not unit:
            continue
        # 単位のない一桁は「3つの理由」等で使われる
        if v < 10 and not unit:
            continue
        # 端数の丸めを許容する（1%以内なら同じ数とみなす）
        if any(abs(v - s) <= max(abs(s) * 0.01, 0.5) for s in src):
            continue
        bad.append(f"{raw}{unit}")
    return sorted(set(bad))


def check_aeo(body: str) -> list[str]:
    lead = re.sub(r"\s", "", re.split(r"\n## ", body)[0])[:300]
    chars = len(re.sub(r"\s", "", re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)))
    lack = []
    if "|---|" not in body and "| --- |" not in body:
        lack.append("表がない")
    if body.count("\n- ") < 3:
        lack.append("箇条書きが少ない")
    if "## まとめ" not in body:
        lack.append("まとめがない")
    if not re.search(r"\*\*.+\*\*", lead):
        lack.append("冒頭に結論がない")
    if body.count("\n## ") < 4:
        lack.append("見出しが4つ未満")
    if chars < MIN_CHARS:
        lack.append(f"{chars}字（{MIN_CHARS}字未満）")
    if len(re.findall(r"\]\(/articles/", body)) < 2:
        lack.append("既存記事への内部リンクが2本未満")
    return lack


def is_duplicate(title: str) -> str | None:
    """既存記事と主題が重なっていないか。単純な語の重なりで見る。"""
    words = set(re.findall(r"[ぁ-んァ-ヶ一-龥A-Za-z]{2,}", title))
    for f in ARTICLES.glob("*.ja.md"):
        m = re.search(r"title: (.+)", f.read_text(encoding="utf-8"))
        if not m:
            continue
        other = set(re.findall(r"[ぁ-んァ-ヶ一-龥A-Za-z]{2,}", m.group(1)))
        if words and len(words & other) / len(words) >= 0.6:
            return f.name
    return None


# --- 実行 ---------------------------------------------------------------

def log(msg: str) -> None:
    print(msg, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / "daily_article.log").open("a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%F %T}  {msg}\n")


def main() -> int:
    dry = "--dry" in sys.argv

    # 同じ日に二度走らせても、その日の記事を上書きしない。
    # cron の再実行や手動実行が重なると、先に書いた記事が消える。
    today_path = ARTICLES / f"news-{datetime.date.today().isoformat()}.ja.md"
    if today_path.exists() and not dry:
        log(f"本日分は作成済み（{today_path.name}）— 何もしない")
        return 0

    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    used = set(state.get("used_urls", []))

    items = json.loads((ROOT / "data" / "news.json").read_text(
        encoding="utf-8"))["items"]
    cands = pick(items, used)
    if not cands:
        log("題材なし — 基準を満たすニュースが無いため今日は書かない")
        return 0

    # 本文を取得できた最初の候補を使う
    item = body = None
    for c in cands:
        log(f"候補: {(c.get('title_ja') or c.get('title'))[:56]}")
        b = fulltext.fetch_body(c.get("url", ""))
        if b and len(b) >= 600:
            item, body = c, b
            break
        log("  出典の本文を取得できないため次の候補へ（推測で書かない）")
        state.setdefault("used_urls", []).append(c.get("url"))
    if not item:
        STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        log("  どの候補も本文を取得できないため今日は書かない")
        return 0
    log(f"題材に決定: {(item.get('title_ja') or item.get('title'))[:56]}")

    # 検査に落ちたら、何が悪かったかを伝えて書き直させる。
    # 一発で通ることは少ないが、指摘を返せばたいてい2回目で通る。
    # 3回試して駄目な日は諦める（無理に出さない）。
    note = ""
    title = article = ""
    for attempt in range(1, 4):
        gen = generate(item, body, note)
        if not gen:
            log(f"  生成に失敗（{attempt}回目）")
            continue
        title, article = gen

        dup = is_duplicate(title)
        if dup:
            log(f"  既存記事と重複（{dup}）のため見送り")
            return 0

        lack = check_aeo(article)
        bad = check_numbers(article, body)
        if not lack and not bad:
            break

        problems = []
        if bad:
            problems.append(
                "次の数値は出典に存在しません。**削除するか、"
                "出典にある数値に置き換えてください**: " + "、".join(bad[:8]))
        if lack:
            problems.append("構成の不足: " + "、".join(lack))
        log(f"  {attempt}回目は不合格 — " + " / ".join(problems)[:120])
        note = ("前回の原稿には次の問題がありました。必ず直してください。\n"
                + "\n".join(f"- {x}" for x in problems) + "\n\n")
    else:
        log("  3回試しても基準を満たさないため、今日は公開しない")
        return 0

    slug = "news-" + datetime.date.today().isoformat()
    path = ARTICLES / f"{slug}.ja.md"
    excerpt = re.sub(r"[*#\n]", "", article)[:100].strip() + "…"
    fm = (f"---\ntitle: {title}\nexcerpt: {excerpt}\n"
          f"tag: ニュース解説\nhero: cover-analysis.jpg\n"
          f"author: UchUchU 編集部\ndate: {datetime.date.today()}\norder: 100\n---\n\n")
    source_note = (
        f"\n\n---\n\n*本記事は "
        f"[{item.get('source_name') or item.get('source') or '出典'}]"
        f"({item.get('url')}) の報道をもとに、編集部が製造業の視点から"
        f"解説したものです。事実関係は出典をご確認ください。*\n")

    if dry:
        log(f"  [dry] 合格。{path.name} は書き込まない")
        print("\n" + title + "\n" + article[:400])
        return 0

    path.write_text(fm + article + source_note, encoding="utf-8")
    state.setdefault("used_urls", []).append(item.get("url"))
    state["used_urls"] = state["used_urls"][-500:]
    STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    log(f"  ✅ 公開: {slug} — {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
