#!/bin/bash
# UchUchU 日次更新。cron から無人で回す前提。
#
# 収集 → 翻訳 → 本文要約 → ビルド → 公開 → 検索エンジン通知 → 成果物を戻す。
# 途中で失敗しても次の実行で取り返せるよう、各段は独立させている
# （収集が落ちても、既存データでのビルドと公開は行う）。
#
# 課金ゼロが絶対条件のため、AIはローカルの claude CLI のみを使い、
# バッチは必ず --model haiku で回す（media_init が環境変数で固定する）。
#
# 環境の準備・ログ・git の往復は3媒体で共通なので、共通フレームに寄せてある。
# 媒体ごとの設定（ブランチ・ログ先・成果物のパス）は media.json が正本。
set -uo pipefail
cd "$(dirname "$0")/.."

FRAME="$HOME/claude_AIR/TOEcompany/メディア事業部/共通/運用/media-daily.sh"
if [ ! -f "$FRAME" ]; then
  echo "共通フレームが見つかりません: $FRAME" >&2
  echo "claude_AIR が同期されていない可能性があります（cd ~/claude_AIR && git pull）" >&2
  exit 1
fi
# shellcheck source=/dev/null
. "$FRAME"

media_init uchuchu || exit 1

# 1. 収集（RSS/API。無料ソースのみ）
media_step "収集" python3 -m uchuchu.collectors.collect_all

# 2. 本文取得と日本語要約
#    1回あたりの件数を絞る。本文取得はネットワーク律速で1件あたり最大2分ほど
#    かかるため、多く回すと runner のタイムアウト（既定900秒）を超えて途中で
#    殺され、収集も公開も巻き添えで止まる。確実に完走する件数に抑える。
#    残りは翌日に持ち越して少しずつ消化する（jobs.yaml でtimeoutも延長済み）。
media_step "本文要約" python3 -m uchuchu.collectors.fulltext --limit=20

# 調達公告の提出期限はPDFにしか書かれていないので、別段で読みに行く。
# 一度読んだものは再取得しないため、日々の負荷は新着分だけで済む。
media_step "調達の締切" python3 -m uchuchu.collectors.procurement_detail --limit=40

# 3. 内部リンク検査 → ビルド → 公開 → IndexNow
media_step "公開" ./tools/deploy.sh

# 4. 収集したデータをリポジトリへ戻す。
#    deploy.sh は dist/ を gh-pages へ送るだけなので、ここで戻さないと
#    翻訳キャッシュや収集結果が実行機の中だけで育ち、別のMacで再現できなくなる。
media_step "データをリポジトリへ反映" media_push "収集データを更新（自動）"

# 4b. データを Neon へ写す（2026-08-24 追加）
#
#     ⚠️ 写しであって正本ではない。サイトが読むのは今までどおりファイルのまま。
#     ここが失敗しても収集・生成・公開は影響を受けない。
#     接続先（~/.config/media/neon_url）が無い実行機では何もせず素通りする。
media_step "Neonへ同期" python3 tools/sync_neon.py

# 5. 状況を1行で残す（週次の振り返りで読む）
python3 - <<'PY'
import json, pathlib, datetime
d = json.loads(pathlib.Path("data/news.json").read_text(encoding="utf-8"))
items = d["items"]
body = sum(1 for i in items if i.get("body_ja"))
line = (f"{datetime.date.today()}\tニュース{len(items)}\t本文{body}"
        f"\t記事{len(list(pathlib.Path('content/articles').glob('*.ja.md')))}")
p = pathlib.Path("data/daily_stats.tsv")
p.write_text((p.read_text(encoding="utf-8") if p.exists() else
              "date\tnews\tbody\tarticles\n") + line + "\n", encoding="utf-8")
print("   " + line.replace("\t", "  "))
PY

media_finish
