#!/bin/bash
# 毎日のニュース解説記事を生成して公開する。cron から無人で回す。
#
# 日次収集（6:30）の直後に走らせる。前夜の海外ニュースが入った状態で選定する。
set -uo pipefail
cd "$(dirname "$0")/.."

# cron の既定 PATH には ~/.local/bin が無く、claude CLI が見つからない。
# さらに認証情報の参照に USER/LOGNAME が要る（無いと "Not logged in" で全滅する）。
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export USER="${USER:-$(id -un)}"
export LOGNAME="$USER"

LOG="$HOME/claude_AIR/TOEcompany/メディア事業部/案件/UchUchU/ログ/daily_article_$(date +%F).log"
mkdir -p "$(dirname "$LOG")"
exec >> "$LOG" 2>&1
echo "════════ $(date '+%F %T') 記事生成 開始 ════════"

. "$(dirname "$0")/lib-git.sh"

# 書き始める前にもう一方のMacの修正を取り込む。
# 取り込まずに書くと、あとで push が衝突して記事が実行機に取り残される。
echo "── コード同期"
git_sync_pull

python3 tools/daily_article.py

# 記事ができていれば公開する（できていない日は何も起きない）
if [ -f "content/articles/news-$(date +%F).ja.md" ]; then
  ./tools/deploy.sh && echo "✅ 公開まで完了"
  # deploy.sh が送るのは dist/ を gh-pages へ、だけ。
  # 記事の元ファイルはここで送らないと実行機の中に閉じ込められる
  # （2026-08-08〜13 の6本が実際にそうなっていた）。
  echo "── 記事をリポジトリへ反映"
  git_sync_push "記事を公開（$(date +%F)・自動）"
else
  echo "今日は記事なし（基準を満たす題材が無かった）"
fi
echo "════════ $(date '+%F %T') 終了 ════════"
