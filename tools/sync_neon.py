#!/usr/bin/env python3
"""UchUchU のデータを Neon（PostgreSQL）へ写す。

⚠️ **写しであって正本ではない。** サイトが読むのは今までどおり
   data/news.json と content/articles/*.md のまま。ここが失敗しても
   収集・生成・公開は影響を受けない。

流すもの:
  data/news.json           → uchuchu.news
  content/articles/*.ja.md → uchuchu.articles

英語版（*.en.md）は日本語版の訳で、slug が同じものが対になっている。
両方入れると同じ slug がぶつかるので、日本語版だけを入れる。

使い方:
  python3 tools/sync_neon.py
  python3 tools/sync_neon.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path.home() / "claude_AIR/TOEcompany/メディア事業部/共通/運用"))

import neon  # noqa: E402

NEWS = ROOT / "data" / "news.json"
ARTICLES = ROOT / "content" / "articles"


def _iso(raw):
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def news_rows() -> list[dict]:
    try:
        data = json.loads(NEWS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"⚠️ news.json を読めません: {e}", file=sys.stderr)
        return []
    items = data.get("items", data if isinstance(data, list) else [])
    rows = []
    for it in items:
        url = (it.get("url") or "").strip()
        if not url:
            continue
        rows.append({
            "url": url,
            "title": (it.get("title") or "")[:1000] or "(無題)",
            "title_ja": it.get("title_ja"),
            "summary": it.get("summary"),
            "source": it.get("source"),
            "lang": it.get("lang"),
            "published": _iso(it.get("published")),
        })
    return rows


def article_rows() -> list[dict]:
    rows = []
    for p in sorted(ARTICLES.glob("*.ja.md")):
        meta, body = neon.read_frontmatter(p)
        rows.append({
            "slug": p.name[: -len(".ja.md")],
            "title": meta.get("title") or p.stem,
            "excerpt": meta.get("excerpt"),
            "published": neon.as_date(meta.get("date")),
            "body": body,
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    news, articles = news_rows(), article_rows()
    print(f"   対象: ニュース{len(news)}件 / 記事{len(articles)}本")
    if args.dry_run:
        print("   --dry-run のため書き込みません")
        return 0
    if not (news or articles):
        print("⚠️ 流すものが1件もありません。読み込みに失敗している可能性があります",
              file=sys.stderr)
        return 1

    def build(cur):
        n = neon.upsert(cur, "uchuchu.news", news, "url")
        a = neon.upsert(cur, "uchuchu.articles", articles, "slug")
        return n + a

    return neon.run_sync("UchUchU", build)


if __name__ == "__main__":
    sys.exit(main())
