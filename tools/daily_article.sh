#!/bin/bash
# 毎日のニュース解説記事を生成して公開する。cron から無人で回す。
#
# 日次収集（6:30）の直後に走らせる。前夜の海外ニュースが入った状態で選定する。
#
# 環境の準備・ログ・git の往復は3媒体で共通なので、共通フレームに寄せてある。
set -uo pipefail
cd "$(dirname "$0")/.."

FRAME="$HOME/claude_AIR/TOEcompany/メディア事業部/共通/運用/media-daily.sh"
if [ ! -f "$FRAME" ]; then
  echo "共通フレームが見つかりません: $FRAME" >&2
  exit 1
fi
# shellcheck source=/dev/null
. "$FRAME"

# 収集の日次とはログを分ける（どちらが何をしたか追えなくなるため）
media_init uchuchu || exit 1
MEDIA_LOG="${MEDIA_LOG%/*}/daily_article_$(date +%F).log"
exec >> "$MEDIA_LOG" 2>&1
echo "──────── $(date '+%F %T') 記事生成 ────────"

python3 tools/daily_article.py

# 記事ができていれば公開する（できていない日は何も起きない）
if [ -f "content/articles/news-$(date +%F).ja.md" ]; then
  media_step "公開" ./tools/deploy.sh
  # deploy.sh が送るのは dist/ を gh-pages へ、だけ。
  # 記事の元ファイルはここで送らないと実行機の中に閉じ込められる
  # （2026-08-08〜13 の6本が実際にそうなっていた）。
  media_step "記事をリポジトリへ反映" media_push "記事を公開（自動）"
else
  echo "今日は記事なし（基準を満たす題材が無かった）"
fi

media_finish
