"""調達公告のPDFから提出期限を取り出す。

締切のない入札一覧は半分しか使えない。応札を検討する人がまず見るのは
「間に合うか」だからだ。ところがAPIの項目に締切は無く、公告PDFの本文に
しか書かれていない。そこでPDFを読んで期限だけを抜く。

書式は発注機関ごとにばらばらで、画像PDFだと1文字も取れないものもある。
取れなかったものは空のままにする（推測で日付を埋めない）。

    python3 -m uchuchu.collectors.procurement_detail --limit=40
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import requests

from .. import config

# 「提出期限」等の見出しから60字以内にある日付だけを拾う。
# 見出しから離れた日付を拾うと、履行期限や説明会の日を締切と誤って出す。
_DEADLINE_HEAD = re.compile(
    r"(入札書[^\n]{0,12}(?:提出|受領)期限|提出期限|受領期限|申込[^\n]{0,6}期限"
    r"|参加[^\n]{0,8}期限|申請書[^\n]{0,8}期限|提案書[^\n]{0,8}期限)"
)
_DATE_WAREKI = re.compile(r"令和\s*(\d{1,2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_DATE_SEIREKI = re.compile(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_TIME = re.compile(r"(\d{1,2})\s*時\s*(\d{1,2})?\s*分?")


def _to_date(text: str) -> str | None:
    """先頭に見つかった日付を YYYY-MM-DD で返す。"""
    m = _DATE_WAREKI.search(text)
    if m:
        # 令和1年 = 2019年
        year = 2018 + int(m.group(1))
        return f"{year:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = _DATE_SEIREKI.search(text)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return None


def extract_deadline(text: str) -> tuple[str | None, str | None]:
    """PDFの平文から (締切日 YYYY-MM-DD, 見出し語) を返す。"""
    for m in _DEADLINE_HEAD.finditer(text):
        window = text[m.end(): m.end() + 60]
        d = _to_date(window)
        if d:
            return d, m.group(1)
    return None, None


def _pdf_text(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=config.HTTP_TIMEOUT,
                         headers={"User-Agent": config.USER_AGENT})
        r.raise_for_status()
    except Exception:
        return None
    if not r.content[:5].startswith(b"%PDF"):
        return None
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(r.content)
        f.flush()
        try:
            out = subprocess.run(["pdftotext", "-layout", f.name, "-"],
                                 capture_output=True, timeout=40)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
    return out.stdout.decode("utf-8", errors="ignore")


def main(limit: int = 40) -> int:
    path = config.DATA_DIR / "procurement.json"
    if not path.exists():
        print("procurement.json がありません。先に収集してください。", file=sys.stderr)
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", [])

    # 未処理のうち新しいものから。1回の実行で上限まで。
    todo = [p for p in items
            if not p.get("deadline_checked") and p.get("url")
            and p.get("file_type") == "pdf"][:limit]
    print(f"[procurement] 締切抽出: 対象 {len(todo)}件")

    found = failed = 0
    for i, p in enumerate(todo, 1):
        text = _pdf_text(p["url"])
        # 読めたかどうかに関わらず既読にする。読めないPDFを毎日引き直さない。
        p["deadline_checked"] = True
        if text:
            d, label = extract_deadline(text)
            if d:
                p["deadline"] = d
                p["deadline_label"] = label
                found += 1
            else:
                failed += 1
        else:
            failed += 1
        if i % 10 == 0 or i == len(todo):
            # 途中で落ちても取れた分は残す
            data["items"] = items
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                            encoding="utf-8")
            print(f"    {i}/{len(todo)}  取得{found} / 不明{failed}")

    data["items"] = items
    data["deadline_updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(1 for p in items if p.get("deadline"))
    print(f"=== 今回 {found}件の締切を取得 / 読めず {failed}件 / 累計 {total}件 ===")
    return 0


if __name__ == "__main__":
    lim = 40
    for a in sys.argv[1:]:
        if a.startswith("--limit="):
            lim = int(a.split("=", 1)[1])
    raise SystemExit(main(lim))
