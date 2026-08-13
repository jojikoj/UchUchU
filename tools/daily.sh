#!/bin/bash
# UchUchU 日次更新。cron から無人で回す前提。
#
# 収集 → 翻訳 → 本文要約 → ビルド → 公開 → 検索エンジン通知。
# 途中で失敗しても次の実行で取り返せるよう、各段は独立させている
# （収集が落ちても、既存データでのビルドと公開は行う）。
#
# 課金ゼロが絶対条件のため、AIはローカルの claude CLI のみを使い、
# バッチは必ず --model haiku で回す（build.py 側ではなく collectors 内で指定）。
set -uo pipefail
cd "$(dirname "$0")/.."

# cron の既定 PATH には ~/.local/bin が含まれず、翻訳・要約に使う
# claude CLI が見つからないまま無音で失敗する。明示しておく。
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

# claude CLI の認証情報はキーチェーンにあり、その参照に USER/LOGNAME を要する。
# cron はこれらを渡さないため、無いと "Not logged in" で全件失敗する。
export USER="${USER:-$(id -un)}"
export LOGNAME="$USER"
export SHELL="${SHELL:-/bin/zsh}"
# バッチは必ず haiku。未指定だと上位モデルを使い、対話の枠まで食い潰す。
export UCHUCHU_BATCH_MODEL=haiku

# 認証まで通るか先に確かめる。ここで落ちていれば要約は全滅するため、
# 気づかず空のまま公開し続けるより、ログに明示して止める方がよい。
if ! claude -p --model haiku "OK" >/dev/null 2>&1; then
  echo "⚠️ claude CLI が使えない（未ログイン/PATH）。要約はスキップされる。"
fi

LOG_DIR="$HOME/claude_AIR/TOEcompany/メディア事業部/案件/UchUchU/ログ"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/daily_$(date +%F).log"
exec >> "$LOG" 2>&1
echo "════════ $(date '+%F %T') 開始 ════════"

step() {   # step <名前> <コマンド...>
  echo "── $1"
  if "${@:2}"; then echo "   ✅ $1"; else echo "   ⚠️ $1 で失敗（続行）"; fi
}

# 0. コードの取り込み
#
#    ⚠️ 2026-08-01 に AIの鬼で起きた事故と同型の穴がこちらにもあった。
#    このスクリプトは git を触っておらず、実行機（Mac mini）は自分の
#    チェックアウトのまま毎日ビルドする。別マシンで直してpushしたコードが
#    永久に本番へ出ない。AIの鬼では7/30のSEO改修が2日間反映されず、
#    /papers/N が8位前後・CTR 0% のまま表示を吸い続けていた。
#    ビルドも公開も「成功」するので watchdog も朝の運用チェックも気づけない。
#
#    運用ブランチは main ではなく gh-pages-tmp なので、現在のブランチに対して pull する。
#    衝突しても日次自体は止めない。ローカルの状態で続行してログに残す。
. "$(dirname "$0")/lib-git.sh"
step "コード同期" git_sync_pull

# 1. 収集（RSS/API。無料ソースのみ）
step "収集" python3 -m uchuchu.collectors.collect_all

# 2. 本文取得と日本語要約
#    1回あたりの件数を絞る。本文取得はネットワーク律速で1件あたり最大2分ほど
#    かかるため、多く回すと runner のタイムアウト（既定900秒）を超えて途中で
#    殺され、収集も公開も巻き添えで止まる。確実に完走する件数に抑える。
#    残りは翌日に持ち越して少しずつ消化する（jobs.yaml でtimeoutも延長済み）。
step "本文要約" python3 -m uchuchu.collectors.fulltext --limit=20

# 3. 内部リンク検査 → ビルド → 公開 → IndexNow
step "公開" ./tools/deploy.sh

# 3.5 収集したデータをリポジトリへ戻す。
#     deploy.sh は dist/ を gh-pages へ送るだけなので、data/ を送らないと
#     翻訳キャッシュや収集結果が実行機の中だけで育ち、別のMacで再現できなくなる。
step "データをリポジトリへ反映" git_sync_push "収集データを更新（$(date +%F)・自動）"

# 4. 状況を1行で残す（週次の振り返りで読む）
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

echo "════════ $(date '+%F %T') 終了 ════════"
