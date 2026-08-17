#!/bin/bash
# dist/ を gh-pages ブランチへ公開する。
#
# 以前は dist/ 内で git init して push していたが、親リポジトリと
# 状態が混ざって「push したのに反映されない」事故が起きた。
# ここでは毎回まっさらな一時リポジトリを作って確実に上書きする。
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)

# 検査はビルドの後に回す。check_links は dist/ の中身も見るため、
# 先に走らせると前回の（＝これから作り直す）生成物を検査してしまい、
# 直したはずの不具合で毎回止まる（2026-08-16、a/ 欠落の残骸で1735件の誤検知）。
python3 -m uchuchu.build

# トップページの有無をここで見る。
# 2026-08-16〜18、dist にトップだけが無い状態のまま3日間 push され、
# uchuchu.tech のトップが404で公開され続けた。ビルドのログは「home」と
# 出ていたし、check_links もトップが無いと黙って素通りしていた。
# 出荷物の骨格は、作った直後に自分の目で確かめる。
for f in index.html en/index.html sitemap.xml feed.xml 404.html; do
  if [ ! -s "dist/$f" ]; then
    echo "❌ ビルド結果に dist/$f がありません。公開を中止します" >&2
    exit 1
  fi
done

python3 tools/check_links.py            # リンク切れがあればここで止める

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cp -R dist/. "$TMP/"
cd "$TMP"
git init -q
git add -A
git -c user.email=noreply@anthropic.com -c user.name=deploy \
    commit -q -m "deploy $(date +%F_%H%M)"

# コミットしたツリーにトップが入っているか。
# dist にあっても、コピーや add の段で落ちれば本番からは消える。
# 送る直前の実物で確かめる。
if ! git ls-files --error-unmatch index.html >/dev/null 2>&1; then
  echo "❌ 公開ツリーに index.html が入っていません。push を中止します" >&2
  exit 1
fi
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

# 公開できたか、外から見て確かめる。
# GitHub Pages の反映には少し間があるので、間隔をあけて数回見る。
# ここで落ちたら日次が失敗として通知するので、404のまま気づかれない事態にはならない。
check_live() {
  local code i
  for i in 1 2 3 4 5 6; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 https://uchuchu.tech/ || echo 000)
    [ "$code" = "200" ] && { echo "✅ 本番のトップページ 200 を確認"; return 0; }
    sleep 20
  done
  echo "❌ 公開後もトップページが HTTP ${code} です（https://uchuchu.tech/）" >&2
  return 1
}
LIVE_OK=0
check_live || LIVE_OK=1

python3 -m uchuchu.indexnow            # 検索エンジンへ更新通知

exit $LIVE_OK
