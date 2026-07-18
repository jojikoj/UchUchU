"""次に書くべき記事を提案する。

ネタ切れは更新停止の最大の原因になる。書く前に毎回考えるのではなく、
「業界がいま何を話しているか」と「自社が何を書いていないか」の差分から
機械的に候補を出す。

判断材料は2つ。

1. **収集済みニュースの話題頻度** — 業界の関心がどこにあるか
2. **既存記事のカバー範囲** — そのうち自分がまだ書いていないもの

出てくるのは「テーマ候補」であって記事そのものではない。
どれを書くかは人が決める。AEOでは、検索意図に対して
一次情報と実務判断を持つ人間の視点が入っているかが効くため、
ここを自動生成に任せない。

    python3 tools/suggest_topics.py
"""
from __future__ import annotations

import collections
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "content" / "articles"
NEWS = ROOT / "data" / "news.json"

# 製造業の読者にとって記事になりうるテーマ。
# 単語の頻度だけを見ると「宇宙」「衛星」のような一般語が上位に来て
# 使えないため、事業機会に結びつく観点であらかじめ束ねておく。
THEMES = [
    ("衛星の量産", ["コンステレーション", "量産", "小型衛星", "スターリンク"]),
    ("月面開発", ["月", "月面", "着陸", "アルテミス", "ローバー"]),
    ("ロケット開発", ["ロケット", "打ち上げ", "エンジン", "再使用", "スターシップ"]),
    ("宇宙デブリ・軌道上サービス", ["デブリ", "軌道上", "除去", "補給", "ドッキング"]),
    ("地球観測・リモートセンシング", ["観測", "リモートセンシング", "SAR", "画像"]),
    ("宇宙通信", ["通信", "アンテナ", "光通信", "中継"]),
    ("有人宇宙・生命維持", ["有人", "宇宙飛行士", "ISS", "宇宙ステーション", "居住"]),
    ("推進系", ["推進", "スラスタ", "イオンエンジン", "燃料", "推進剤"]),
    ("宇宙用電子部品", ["半導体", "電子", "センサ", "耐放射線", "計算機"]),
    ("材料・構造", ["材料", "複合材", "構造", "軽量", "3Dプリント", "積層造形"]),
    ("試験・評価", ["試験", "検証", "実証", "評価"]),
    ("政策・予算・制度", ["政策", "予算", "法", "規制", "支援", "補助"]),
    ("安全保障", ["安全保障", "防衛", "偵察"]),
    ("宇宙探査", ["探査", "火星", "小惑星", "サンプル"]),
]


def article_text() -> str:
    return "\n".join(f.read_text(encoding="utf-8")
                     for f in ARTICLES.glob("*.ja.md"))


def main() -> int:
    news = json.loads(NEWS.read_text(encoding="utf-8"))["items"]
    corpus = article_text()

    # 各テーマがニュースで何回話題になっているか
    hits = collections.Counter()
    for item in news:
        blob = " ".join(str(item.get(k) or "") for k in
                        ("title_ja", "title", "summary_ja", "summary"))
        for theme, keys in THEMES:
            if any(k in blob for k in keys):
                hits[theme] += 1

    # 既存記事での扱いの厚さ
    covered = {theme: sum(corpus.count(k) for k in keys)
               for theme, keys in THEMES}

    rows = []
    for theme, _ in THEMES:
        n, c = hits[theme], covered[theme]
        # 業界の話題量に対して自分の記述が薄いほど、書く価値が高い
        gap = n / (c + 5)
        rows.append((gap, n, c, theme))
    rows.sort(reverse=True)

    print(f"=== 記事ネタ候補（ニュース{len(news)}件・記事"
          f"{len(list(ARTICLES.glob('*.ja.md')))}本を分析）===\n")
    print(f"{'テーマ':28} {'話題数':>6} {'既存言及':>8}  優先")
    print("-" * 58)
    for gap, n, c, theme in rows:
        mark = "★★★" if gap >= 8 else "★★" if gap >= 3 else "★"
        print(f"{theme:28} {n:>6} {c:>8}  {mark}")

    print("\n【読み方】")
    print("  話題数が多く既存言及が少ないテーマ＝業界は語っているが自分は書いていない領域。")
    print("  ただし機械的な差分でしかない。製造業の受注につながるかは人が判断すること。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
