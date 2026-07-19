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

LOG="$HOME/claude_AIR/TOEcompany/コンテンツ部/案件/UchUchU/ログ/daily_article_$(date +%F).log"
mkdir -p "$(dirname "$LOG")"
exec >> "$LOG" 2>&1
echo "════════ $(date '+%F %T') 記事生成 開始 ════════"

python3 tools/daily_article.py

# 記事ができていれば公開する（できていない日は何も起きない）
if [ -f "content/articles/news-$(date +%F).ja.md" ]; then
  ./tools/deploy.sh && echo "✅ 公開まで完了"
else
  echo "今日は記事なし（基準を満たす題材が無かった）"
fi
echo "════════ $(date '+%F %T') 終了 ════════"
