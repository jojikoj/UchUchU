#!/bin/bash
# dist/ を gh-pages ブランチへ公開する。
#
# 以前は dist/ 内で git init して push していたが、親リポジトリと
# 状態が混ざって「push したのに反映されない」事故が起きた。
# ここでは毎回まっさらな一時リポジトリを作って確実に上書きする。
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)

python3 tools/check_links.py            # リンク切れがあればここで止める
python3 -m uchuchu.build

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cp -R dist/. "$TMP/"
cd "$TMP"
git init -q
git add -A
git -c user.email=noreply@anthropic.com -c user.name=deploy \
    commit -q -m "deploy $(date +%F_%H%M)"
# push の認証。
# cron 環境では osxkeychain（gitの既定 credential helper）が
# ロック状態だと読めず "could not read Username" で失敗する（6:40の実例）。
# gh CLI のトークンは最小環境でも読めるので、あればそれを使う。
# トークンは実行時に取得し、ファイルにもログにも残さない。
REPO="github.com/jojikoj/UchUchU.git"
push_repo() {
  local token
  if token=$(gh auth token 2>/dev/null) && [ -n "$token" ]; then
    # -c で helper を空にし、キーチェーンを一切触らせない
    git -c credential.helper= \
        push -q -f "https://x-access-token:${token}@${REPO}" HEAD:gh-pages
  else
    git push -q -f "https://${REPO}" HEAD:gh-pages   # フォールバック
  fi
}
# 一時的な認証・ネットワーク不調に備えて2回まで試す
if push_repo || { sleep 5; push_repo; }; then
  echo "✅ gh-pages へ push しました"
else
  echo "❌ push に失敗（次回の実行で再度 push されます）"
  exit 1
fi

cd "$ROOT"
python3 -m uchuchu.indexnow            # 検索エンジンへ更新通知
