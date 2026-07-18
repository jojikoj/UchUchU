"""収集オーケストレーター。

各ソースを順に取得し、失敗はスキップして継続（フェイルソフト）。
結果を data/*.json に保存する。build.py がこれを読んでサイトを生成。

実行:
    python -m uchuchu.collectors.collect_all
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from .. import config
from . import sources, translate


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save(name: str, payload: dict) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = config.DATA_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  saved {path.relative_to(config.ROOT)}")


def _sort_key_desc(items, key="published"):
    return sorted(items, key=lambda x: (x.get(key) or ""), reverse=True)


def collect_news() -> dict:
    print("[news] collecting...")
    all_items: list[dict] = []
    per_source = {}
    for src in config.NEWS_SOURCES:
        try:
            items = sources.fetch_news_source(src)
            all_items.extend(items)
            per_source[src["id"]] = len(items)
            print(f"  ok  {src['id']:16s} {len(items):3d} items")
        except Exception as e:  # フェイルソフト
            per_source[src["id"]] = 0
            print(f"  FAIL {src['id']:16s} {type(e).__name__}: {e}", file=sys.stderr)
    # 重複URL除去
    seen, deduped = set(), []
    for it in _sort_key_desc(all_items):
        u = it.get("url")
        if u and u in seen:
            continue
        seen.add(u)
        deduped.append(it)
    deduped = deduped[: config.NEWS_LIMIT]
    _maybe_translate_news(deduped)
    return {"generated_at": _now_iso(), "count": len(deduped),
            "sources": per_source, "items": deduped}


def _maybe_translate_news(items: list[dict]) -> None:
    """argostranslate があれば各記事に相手言語の訳を付ける。無ければ何もしない。

    これにより日本語サイトでは英語ソースが日本語で、
    英語サイトでは日本語ソースが英語で読める。
    """
    if not translate.available():
        print("  [translate] 翻訳エンジンなし — 原文のまま掲載します")
        return
    # 英→日のみ翻訳する。
    # 日→英は機械翻訳の品質が公開に耐えないため行わず、
    # 英語サイトには英語ソースのみを掲載する（build.py 側で振り分け）。
    targets = [it for it in items if it.get("lang") == "en"]
    if not targets:
        return
    print(f"  [translate] 英→日 翻訳開始（{len(targets)}件 / backend={translate.backend_name()}）")
    filled = translate.translate_english_items(targets)
    print(f"  [translate] {filled}/{len(targets)} 件に日本語訳を付与")


def collect_launches() -> dict:
    print("[launches] collecting...")
    try:
        items = sources.fetch_launches()
        print(f"  ok  {len(items)} launches")
    except Exception as e:
        items = []
        print(f"  FAIL launches {type(e).__name__}: {e}", file=sys.stderr)
    items = items[: config.LAUNCHES_LIMIT]
    return {"generated_at": _now_iso(), "count": len(items), "items": items}


def collect_papers() -> dict:
    print("[papers] collecting...")
    try:
        items = sources.fetch_papers()
        print(f"  ok  {len(items)} papers")
    except Exception as e:
        items = []
        print(f"  FAIL papers {type(e).__name__}: {e}", file=sys.stderr)
    items = _sort_key_desc(items)[: config.PAPERS_LIMIT]
    return {"generated_at": _now_iso(), "count": len(items), "items": items}


def main() -> int:
    print(f"=== UchUchU collect @ {_now_iso()} ===")
    news = collect_news()
    launches = collect_launches()
    papers = collect_papers()

    _save("news.json", news)
    _save("launches.json", launches)
    _save("papers.json", papers)

    total = news["count"] + launches["count"] + papers["count"]
    print(f"=== done: news={news['count']} launches={launches['count']} "
          f"papers={papers['count']} (total {total}) ===")
    # 全滅なら失敗扱い（CIで気付けるように）
    return 0 if total > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
