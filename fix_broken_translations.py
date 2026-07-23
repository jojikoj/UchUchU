#!/usr/bin/env python3
"""翻訳キャッシュの壊れたエントリを検出・修正するツール。

機械翻訳がタイムアウトや上限エラーで失敗した場合、
キャッシュに不正なテキスト（例: 「地球が太陽の風が〜」）が保存されることがある。

このツールは:
1. 壊れたエントリを検出（日本語として異常な文字列パターン）
2. それらを削除 or マーク
3. 再翻訳の対象にする
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
CACHE_FILE = DATA_DIR / "translations.json"


def looks_broken(text: str) -> bool:
    """日本語として異常な特徴を検出。"""
    if not text:
        return False

    # パターン1: 同じ音の繰り返し（「るるるる」など）
    if re.search(r'([あ-ん])\1{3,}', text):
        return True

    # パターン2: 不自然な長音の繰り返し（「゛゛゛」など）
    if re.search(r'[゛゜゛゜]{3,}', text):
        return True

    # パターン3: 句読点だけ（「。。。」など）
    if re.match(r'^[。、！？\s]+$', text):
        return True

    # パターン4: 英語/数字と日本語が不自然に混在（翻訳失敗の典型）
    # 例: 「地球が太陽の風」= 日本語らしき単語が文法的におかしい
    # これは難しいので、複数の奇妙なパターンが同時にあれば疑わしい
    has_mixed_lang = bool(re.search(r'[a-z]{10,}', text, re.I))  # 長い英単語
    has_repeated_hiragana = bool(re.search(r'([あ-ん]){6,}', text))

    if has_mixed_lang and has_repeated_hiragana:
        return True

    # パターン5: 明らかに翻訳失敗のシグナル語
    if any(sig in text for sig in ['地球が太陽', 'るるるる', 'う゛ゥ', 'ッッッ']):
        return True

    return False


def fix_cache():
    """壊れたエントリを検出・削除。"""
    if not CACHE_FILE.exists():
        print(f"Cache file not found: {CACHE_FILE}")
        return 1

    try:
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"❌ Cache JSON decode error: {e}")
        return 1

    broken_count = 0
    fixed_entries = []

    for url, entry in list(cache.items()):
        title_ja = entry.get("title_ja", "")
        summary_ja = entry.get("summary_ja", "")

        title_broken = looks_broken(title_ja)
        summary_broken = looks_broken(summary_ja)

        if title_broken or summary_broken:
            broken_count += 1
            fixed_entries.append({
                "url": url,
                "title": title_ja[:60] if title_ja else "(empty)",
                "summary": summary_ja[:80] if summary_ja else "(empty)",
            })
            # 壊れたエントリを削除
            del cache[url]
            print(f"  🗑️  {url[:60]}...")

    if broken_count == 0:
        print("✅ No broken entries found.")
        return 0

    # キャッシュを上書き保存
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n✅ Fixed {broken_count} broken entries.")
    print(f"   Cache file: {CACHE_FILE}")
    print(f"\n📝 Deleted entries (will be re-translated on next run):")
    for entry in fixed_entries:
        print(f"   • {entry['url']}")
        if entry['title'] != "(empty)":
            print(f"     title: {entry['title']}")
        if entry['summary'] != "(empty)":
            print(f"     summary: {entry['summary']}")

    print(f"\n💡 Next step: Run './run.sh publish' to re-collect and re-translate.")
    return 0


if __name__ == "__main__":
    sys.exit(fix_cache())
