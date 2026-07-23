"""元記事の本文を取得し、独自の日本語要約を作る。

RSSが配信する要約は50〜150字程度で、しかも途中で切れていることが多い。
それだけを載せた記事ページは読者にとって価値がなく、
検索エンジンからも「中身の薄いページ」と見なされる。

そこで元記事の本文を取得し、**250字程度の日本語要約**を生成する。
本文そのものは保存も掲載もしない（著作権は元の発信者にあるため）。
生成するのは要約であって転載ではない。

守っていること:
  - robots.txt を必ず確認し、拒否されているサイトは取得しない
  - User-Agent に連絡先を含め、身元を明示する
  - リクエスト間隔を空け、相手サーバーに負荷をかけない
  - 本文は要約生成にのみ使い、保存しない
  - 掲載時は必ず出典と元記事リンクを併記する
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse as up
import urllib.robotparser as rp

import requests

from .. import config
from . import translate

try:
    import trafilatura
except ImportError:
    trafilatura = None

UA = "UchUchU/1.0 (+https://uchuchu.tech; space industry media)"
FETCH_TIMEOUT = 20
POLITE_INTERVAL = 1.5      # 同一ホストへの連続アクセス間隔（秒）
MIN_BODY = 400             # これ未満なら解説に足る本文が取れていないと判断
# 生成する解説文の字数。
# 以前は250字の短い引用要約にしていたが、それだけの記事ページは
# 読者にも検索エンジンにも「中身が薄い」と見なされる。
# そこで元記事の事実を土台にした**独自の解説**を1,000字以上で書く。
# ただし上限を設けないと元記事をほぼ全訳した転載に近い文章になるため、
# 下限だけでなく上限も必ず設ける。
MIN_CHARS = 1000           # これ未満は不合格（本文として載せない）
TARGET_CHARS = 1200        # 生成する解説の目安
MAX_CHARS = 1600           # これを超えたら書きすぎ（転載化）として弾く

# 要約生成に使うモデル。数百件を回す定型処理なので軽量モデルを指定する。
# 指定しないとCLIの既定モデル（＝対話と同じ上位モデル）が使われ、
# 利用枠を食い潰して途中から全件失敗する。実際に414件が失敗した。
BATCH_MODEL = os.environ.get("UCHUCHU_BATCH_MODEL", "haiku")

_robots_cache: dict[str, rp.RobotFileParser | None] = {}
_last_access: dict[str, float] = {}


def _allowed(url: str) -> bool:
    """robots.txt で許可されているかを確認する。判断できない場合は取得しない。"""
    host = up.urlparse(url).netloc
    if host not in _robots_cache:
        parser = rp.RobotFileParser()
        parser.set_url(f"https://{host}/robots.txt")
        try:
            parser.read()
            _robots_cache[host] = parser
        except Exception:
            _robots_cache[host] = None
    parser = _robots_cache[host]
    if parser is None:
        return False          # 確認できないなら取りに行かない
    try:
        return parser.can_fetch(UA, url)
    except Exception:
        return False


def _wait(host: str) -> None:
    last = _last_access.get(host, 0.0)
    delta = time.time() - last
    if delta < POLITE_INTERVAL:
        time.sleep(POLITE_INTERVAL - delta)
    _last_access[host] = time.time()


def fetch_body(url: str) -> str:
    """元記事の本文を返す。取得できない場合は空文字。"""
    if trafilatura is None or not url:
        return ""
    if not _allowed(url):
        return ""
    host = up.urlparse(url).netloc
    _wait(host)
    try:
        r = requests.get(url, timeout=FETCH_TIMEOUT, headers={"User-Agent": UA})
        r.raise_for_status()
    except Exception:
        return ""
    try:
        text = trafilatura.extract(
            r.text, include_comments=False, include_tables=False,
            no_fallback=False) or ""
    except Exception:
        return ""
    return text.strip()


# --- 要約生成 -----------------------------------------------------------
_PROMPT = """あなたは日本の製造業に向けた宇宙産業メディアの編集者です。
以下の英語記事の本文を読み、日本語の**独自の解説文**を書いてください。

これは元記事を翻訳・転載するものではありません。
元記事が報じた事実を土台に、読者（部品・装置・素材を作る製造業）に向けて
「何が起きたのか」「それがどういう意味を持つのか」を自分の言葉で書きます。

構成（この順で、通常の文章として書く。見出し・箇条書きは使わない）:
1. 冒頭で「何が起きたか」を1〜2文で言い切る
2. その背景・経緯を、元記事の事実にもとづいて説明する
3. この出来事が宇宙産業やサプライチェーンにとって持つ意味を述べる
4. 日本の製造業・部品サプライヤーの視点で、どう関わりうるかに簡潔に触れる

要件:
- **全体で1000字以上、1200字前後。1600字を超えないこと**
- 3〜5段落。段落の間は必ず空行で区切る
- 元記事に無い事実・数字・企業名を足さない。市場規模などを補いたくなっても
  数字では書かず「大きい」「増えている」のように言葉で書く
- 推測を断定で書かない。「〜と考えられる」「〜の可能性がある」と明示する
- 煽り表現（衝撃・すぎる・もう終わり）や「いかがでしたか」等の字数稼ぎを書かない
- 固有名詞は日本で一般的な表記に（Falcon 9→ファルコン9 など）
- 敬体（です・ます）ではなく常体（だ・である）で書く
- 出力は解説本文のみ。タイトル・前置き・説明・引用符・見出し記号は書かない

記事タイトル: {title}

記事本文:
{body}
"""


def summarize(title: str, body: str) -> str:
    """本文から1000字以上の日本語解説を生成する。失敗時は空文字。"""
    if not body or len(body) < MIN_BODY:
        return ""
    if not translate.claude_available():
        return ""
    # 長すぎる本文は先頭を使う（結論が先に書かれる記事が多いため）
    src = body[:6000]
    prompt = _PROMPT.format(title=title, body=src)
    import subprocess
    try:
        proc = subprocess.run(
            [translate.CLAUDE_BIN, "--model", BATCH_MODEL, "-p", prompt],
            capture_output=True, text=True, timeout=300)
    except Exception as e:
        print(f"    [summary] 呼び出し失敗: {type(e).__name__}", file=sys.stderr)
        return ""
    if proc.returncode != 0:
        return ""
    out = proc.stdout.strip()
    # コードフェンスが付いた場合は剥がす
    if out.startswith("```"):
        out = out.split("```")[1] if "```" in out[3:] else out
        out = out.lstrip("markdown").lstrip("\n")
    return out.strip()


def enrich(items: list[dict], limit: int | None = None,
           save_cb=None, save_every: int = 5) -> int:
    """記事に本文由来の要約（body_ja）を付与する。付与できた件数を返す。

    既に body_ja がある記事はスキップするため、
    再実行しても新着分だけが処理される。

    全件で数時間かかるため、save_every 件ごとに save_cb を呼んで
    途中経過を保存する。中断しても、そこまでの成果は失われない。
    """
    targets = [it for it in items if not it.get("body_ja") and it.get("url")]
    if limit:
        targets = targets[:limit]
    if not targets:
        print("  [fulltext] 新規対象なし")
        return 0

    print(f"  [fulltext] 本文取得＋要約生成: {len(targets)}件")
    done = skipped = 0
    # 要約生成が連続で失敗する場合、claude CLI 側が使えなくなっている
    # 可能性が高い。空振りを続けても意味がないので打ち切る。
    consecutive_fail = 0
    for i, it in enumerate(targets, 1):
        body = fetch_body(it["url"])
        if not body or len(body) < MIN_BODY:
            it["body_skip"] = "no_body"
            skipped += 1
        else:
            summary = summarize(it.get("title", ""), body)
            # 合格条件: 1000字以上・上限内・崩壊していない。
            # 以前は下限を300字に置きつつプロンプトで「300字以内」と指示しており、
            # 矛盾で大半が不合格になっていた（body_ja が224件で頭打ち）。
            ok = (summary
                  and MIN_CHARS <= len(summary) <= MAX_CHARS
                  and not translate.looks_degenerate_ja(summary))
            if ok:
                it["body_ja"] = summary
                it["body_chars"] = len(summary)
                done += 1
                consecutive_fail = 0
            else:
                # 一時的な失敗と恒久的な失敗を区別できないため、
                # フラグは付けずに次回の再試行対象として残す
                skipped += 1
                consecutive_fail += 1
                if consecutive_fail >= 8:
                    print("    要約生成が8件連続で失敗。"
                          "利用上限に達した可能性が高いため中断する。",
                          file=sys.stderr)
                    if save_cb:
                        save_cb()
                    return done
        # 途中経過を保存する（4時間かかる処理を最後まで抱え込まない）
        if save_cb and (i % save_every == 0 or i == len(targets)):
            save_cb()
        if i % 10 == 0 or i == len(targets):
            print(f"    {i}/{len(targets)}  生成{done} / スキップ{skipped}", flush=True)
    return done


def main() -> int:
    path = config.DATA_DIR / "news.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    limit = None
    for a in sys.argv[1:]:
        if a.startswith("--limit="):
            limit = int(a.split("=", 1)[1])
    def save():
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)   # 書き込み中の破損を避けるため原子的に置き換える

    n = enrich(data["items"], limit=limit, save_cb=save)
    save()
    total = sum(1 for x in data["items"] if x.get("body_ja"))
    print(f"=== 今回 {n}件生成 / 累計 {total}件が本文要約つき ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
