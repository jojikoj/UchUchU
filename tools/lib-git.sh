#!/bin/bash
# 日次スクリプトが使う git 同期の共通処理。
#
# なぜ必要か（2026-08-13 に判明した穴）:
#   このリポは Mac mini（日次自動実行）と MacBook Air（手作業）の2台で扱っている。
#   daily.sh には「コードを取り込む」pull を足してあったが、**push が無かった**。
#   deploy.sh が公開するのは dist/ を gh-pages へ force-push するところまでで、
#   生成した記事の元ファイル（content/articles/news-*.ja.md）はどこにも送られない。
#
#   結果、2026-08-08〜08-13 の6本は本番サイトには出ているのに、リポには存在せず、
#   MacBook Air から見ると「8/5 以降が止まっている」ように見えていた。
#   実体は mini のローカルにしか無く、mini が壊れれば HTML しか残らない状態だった。
#
#   AIの鬼で起きた「pushしたコードが実行機に届かない」の裏返しにあたる。
#   あちらは pull が無く、こちらは push が無かった。
#
# 方針:
#   - 処理の前に運用ブランチを取り込む（未コミット変更は --autostash で退避）
#   - 記事とデータが増えたら commit して push し、もう一方のMacから見える状態にする
#   - 失敗しても日次更新は止めない。ログに理由を残す（黙って失敗するのが一番危ない）

GIT_BOT_NAME="uchuchu-bot"
GIT_BOT_EMAIL="joe@gtoe.info"

git_as_bot() {
  git -c user.name="$GIT_BOT_NAME" -c user.email="$GIT_BOT_EMAIL" "$@"
}

_git_branch() {
  git rev-parse --abbrev-ref HEAD 2>/dev/null
}

# 運用ブランチ（main ではなく gh-pages-tmp）を取り込む
git_sync_pull() {
  git remote get-url origin >/dev/null 2>&1 || return 0
  local br
  br=$(_git_branch) || return 1
  [ -z "$br" ] || [ "$br" = "HEAD" ] && {
    echo "   ⚠️ detached HEAD。自動pullが効かないため手動で確認してください"
    return 1
  }

  git fetch origin "$br" --quiet 2>/dev/null || {
    echo "   ⚠️ fetch失敗（ローカルのまま続行）"
    return 1
  }

  local behind
  behind=$(git rev-list --count "HEAD..origin/$br" 2>/dev/null || echo 0)
  [ "$behind" = "0" ] && { echo "   最新（取り込むものなし）"; return 0; }

  echo "   origin/$br に未取込 ${behind} 件 → 取り込む"
  if git_as_bot pull --rebase --autostash --quiet origin "$br" 2>/dev/null; then
    echo "   取り込み完了: $(git log --oneline -1)"
    return 0
  fi
  git rebase --abort 2>/dev/null || true
  echo "   ⚠️ 取り込みが衝突。ローカルの状態で続行（要手動解消）"
  return 1
}

# 生成物のうち「元ファイル」だけを送る。dist/ は .gitignore 済みなので入らない。
#   $1 … コミットメッセージ
git_sync_push() {
  git remote get-url origin >/dev/null 2>&1 || return 0
  local br msg
  br=$(_git_branch)
  msg="${1:-日次更新（自動）}"
  [ -z "$br" ] || [ "$br" = "HEAD" ] && return 1

  # 記事とデータのみ。設定やコードの実験的な変更を巻き込まない
  git add content/articles data/news.json data/launches.json data/papers.json \
          data/translations.json data/daily_article_state.json data/daily_stats.tsv 2>/dev/null

  if git diff --cached --quiet 2>/dev/null; then
    echo "   送るものなし"
    return 0
  fi

  git_as_bot commit -q -m "$msg" || { echo "   ⚠️ commit失敗"; return 1; }

  if git push --quiet origin "HEAD:$br" 2>/dev/null; then
    echo "   push 完了: $(git log --oneline -1)"
    return 0
  fi

  # 相手が先に進めていた場合は取り込んでからもう一度だけ試す
  echo "   push が拒否された → 取り込み直して再試行"
  if git_sync_pull && git push --quiet origin "HEAD:$br" 2>/dev/null; then
    echo "   push 完了（再試行）"
    return 0
  fi
  echo "   ⚠️ push失敗。生成した記事がこのMacにしか無い状態です（要手動: git push origin $br）"
  return 1
}
