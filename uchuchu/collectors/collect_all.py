"""収集オーケストレーター。

各ソースを順に取得し、失敗はスキップして継続（フェイルソフト）。
結果を data/*.json に保存する。build.py がこれを読んでサイトを生成。

実行:
    python -m uchuchu.collectors.collect_all
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

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


def _load_existing(name: str) -> list[dict]:
    """前回の収集結果を読む（アーカイブ蓄積のため）。"""
    path = config.DATA_DIR / name
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("items", [])
    except (json.JSONDecodeError, OSError):
        return []


def _merge_archive(new_items: list[dict], old_items: list[dict],
                   limit: int, key: str = "url") -> list[dict]:
    """新着を既存アーカイブに統合する。

    毎回上書きせず積み上げることで、日を追うごとに記事数が増える。
    既存側の項目（翻訳結果など）は保持する。
    """
    by_key: dict[str, dict] = {}
    for it in old_items:
        k = it.get(key)
        if k:
            by_key[k] = it
    for it in new_items:
        k = it.get(key)
        if not k:
            continue
        if k in by_key:
            # 既存を土台に新しい情報で更新（翻訳結果は消さない）
            merged = dict(by_key[k])
            merged.update({kk: vv for kk, vv in it.items() if vv})
            by_key[k] = merged
        else:
            by_key[k] = it
    return _sort_key_desc(list(by_key.values()))[:limit]


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
    # 既存アーカイブに統合（積み上げ式）
    old = _load_existing("news.json")
    merged = _merge_archive(all_items, old, config.NEWS_LIMIT)
    print(f"  今回取得 {len(all_items)}件 + 既存 {len(old)}件 → 統合後 {len(merged)}件")

    _maybe_translate_news(merged)
    return {"generated_at": _now_iso(), "count": len(merged),
            "sources": per_source, "items": merged}


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
    english = [it for it in items if it.get("lang") == "en"]
    if not english:
        return

    # 既訳キャッシュを適用（URLキー）。同じ記事を二度訳さない。
    cache = _load_translation_cache()
    reused = 0
    for it in english:
        hit = cache.get(it.get("url", ""))
        if hit and not it.get("title_ja"):
            it["title_ja"] = hit.get("title_ja", "")
            it["summary_ja"] = hit.get("summary_ja", "")
            it["translated_ja"] = True
            reused += 1

    targets = [it for it in english if not it.get("translated_ja")]
    print(f"  [translate] 英語記事{len(english)}件: 既訳流用 {reused}件 / 新規翻訳 {len(targets)}件"
          f" (backend={translate.backend_name()})")
    if not targets:
        return

    filled = translate.translate_english_items(targets)

    # 訳文の後始末。機械翻訳は金額・単位で崩れやすく、
    # 「$ 7.1百万賞を受賞」のような見出しがそのまま公開されたことがある。
    # また argostranslate は「揺るぐるるるるるる」のような繰り返し崩壊を
    # 起こす。崩れた訳はフラグを立てるだけでは公開されてしまうため、
    # ここで破棄して英語原文に戻し、次回の再翻訳対象に残す。
    purged = 0
    for it in english:
        for key in ("title_ja", "summary_ja"):
            if it.get(key):
                it[key] = translate.fix_units(it[key])
        title_ja = it.get("title_ja", "")
        if title_ja and translate.looks_broken(title_ja):
            # 見出しが壊れているなら訳ごと捨てる。英語原文で表示され、
            # translated_ja を落とすことで次回もう一度訳しにいく。
            it.pop("title_ja", None)
            it.pop("summary_ja", None)
            it["translated_ja"] = False
            purged += 1
        elif it.get("summary_ja") and translate.looks_broken(it["summary_ja"]):
            # 見出しは無事だが要約だけ壊れている場合は要約だけ捨てる。
            it.pop("summary_ja", None)
        it["title_ja_broken"] = bool(
            it.get("title_ja") and translate.looks_broken(it["title_ja"]))
    print(f"  [translate] {filled}/{len(targets)} 件を新規翻訳"
          + (f"（崩壊{purged}件を破棄し英語原文に戻した）" if purged else ""))
    _save_translation_cache(cache, english)


def _load_translation_cache() -> dict:
    path = config.DATA_DIR / "translations.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_translation_cache(cache: dict, items: list[dict]) -> None:
    """翻訳結果をURLキーで保存する。次回以降の再翻訳を防ぐ。

    品質が悪い訳（タイムアウト失敗など）はキャッシュに入れない。
    """
    skipped = 0
    for it in items:
        url = it.get("url")
        title_ja = it.get("title_ja", "")
        summary_ja = it.get("summary_ja", "")

        if url and title_ja:
            # キャッシュに保存する前に品質チェック
            # 壊れた訳は載せず、次回再翻訳する
            if not (translate.looks_broken(title_ja) or translate.looks_broken(summary_ja)):
                cache[url] = {"title_ja": title_ja, "summary_ja": summary_ja}
            else:
                skipped += 1

    # 上限（アーカイブ上限の2倍まで保持）
    if len(cache) > config.NEWS_LIMIT * 2:
        cache = dict(list(cache.items())[-config.NEWS_LIMIT * 2:])
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    (config.DATA_DIR / "translations.json").write_text(
        json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  [translate] キャッシュ保存: {len(cache)}件" + (f" (品質チェックで{skipped}件スキップ)" if skipped else ""))


def collect_launches() -> dict:
    print("[launches] collecting...")
    try:
        items = sources.fetch_launches()
        print(f"  ok  {len(items)} launches")
    except Exception as e:
        items = []
        print(f"  FAIL launches {type(e).__name__}: {e}", file=sys.stderr)
    # 打ち上げは id で統合（予定→実績へ状態が変わるため上書き更新）
    old = _load_existing("launches.json")
    by_id = {l["id"]: l for l in old if l.get("id")}
    fetched_ids = set()
    for l in items:
        if l.get("id"):
            by_id[l["id"]] = l
            fetched_ids.add(l["id"])
    merged = list(by_id.values())

    # 今回のAPI応答に含まれず、予定時刻を24時間以上過ぎた「予定」は降格する。
    # 中止・無期限延期になった打ち上げが upcoming のまま残り、
    # 一覧の先頭に「まもなく」として居座り続けるため（実測あり）。
    # 末尾が Z と +00:00 で混在するため、秒までの19文字だけで比較する。
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()[:19]
    demoted = 0
    for l in merged:
        if (l.get("upcoming") and l.get("id") not in fetched_ids
                and (l.get("net") or "")[:19] < cutoff):
            l["upcoming"] = False
            l["stale"] = True
            demoted += 1
    if demoted:
        print(f"  更新の止まった予定 {demoted}件を実績側へ降格")
    upcoming = sorted([l for l in merged if l.get("upcoming")],
                      key=lambda x: x.get("net") or "")
    past = sorted([l for l in merged if not l.get("upcoming")],
                  key=lambda x: x.get("net") or "", reverse=True)
    merged = (upcoming + past)[: config.LAUNCHES_LIMIT]
    print(f"  統合後 {len(merged)}件（予定{len(upcoming)} / 実績{len(past)}）")
    return {"generated_at": _now_iso(), "count": len(merged), "items": merged}


def collect_papers() -> dict:
    print("[papers] collecting...")
    try:
        items = sources.fetch_papers()
        print(f"  ok  {len(items)} papers")
    except Exception as e:
        items = []
        print(f"  FAIL papers {type(e).__name__}: {e}", file=sys.stderr)
    old = _load_existing("papers.json")
    merged = _merge_archive(items, old, config.PAPERS_LIMIT)
    print(f"  統合後 {len(merged)}件")
    return {"generated_at": _now_iso(), "count": len(merged), "items": merged}


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
