"""記事内の内部リンクが実在するか検査する。

記事を書くときスラッグを間違えると404になるが、
ビルドは通ってしまうため気づけない。デプロイ前にここで落とす。

    python3 tools/check_links.py   # 壊れていれば exit 1
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "content" / "articles"

# 記事以外で存在が保証されているパス
STATIC_PATHS = {
    "/", "/news/", "/launches/", "/papers/", "/articles/",
    "/companies/", "/contact/", "/advertise/", "/faq/", "/topics/",
}


def check_dist() -> list[str]:
    """生成物 dist/ の内部リンクが実在するか、全ページ分を検査する。

    記事の markdown だけを見ていたため、テンプレート側のリンクの誤りに
    気づけなかった。実際、関連記事・関連論文のリンクが a/ p/ の欠落で
    全ページ404、記事が0件になったソースへのリンクも404のまま
    数週間公開されていた（2026-08-15 発見、131本）。
    ここで生成物そのものを見れば、同じ壊れ方は二度と出荷されない。
    """
    dist = ROOT / "dist"
    if not (dist / "index.html").exists():
        return []
    href = re.compile(r'href="([^"#?]+)"')
    broken: dict[str, int] = {}
    for f in dist.rglob("index.html"):
        base = "/" + str(f.parent.relative_to(dist)).replace("\\", "/")
        if base == "/.":
            base = "/"
        for link in href.findall(f.read_text(encoding="utf-8", errors="ignore")):
            if link.startswith(("http", "mailto:", "//", "javascript:", "webcal:")):
                continue
            path = link if link.startswith("/") else base.rstrip("/") + "/" + link
            # ブラウザと同じくルートより上には行けない
            parts: list[str] = []
            for seg in path.split("/"):
                if seg in ("", "."):
                    continue
                if seg == "..":
                    if parts:
                        parts.pop()
                else:
                    parts.append(seg)
            target = dist.joinpath(*parts)
            ok = target.exists() if target.suffix else (target / "index.html").exists()
            if not ok:
                key = "/" + "/".join(parts)
                broken[key] = broken.get(key, 0) + 1
    return [f"{url}（{n}箇所から参照）" for url, n in
            sorted(broken.items(), key=lambda kv: -kv[1])]


def main() -> int:
    slugs = {f.name.replace(".ja.md", "") for f in ARTICLES.glob("*.ja.md")}
    bad = []
    for f in sorted(ARTICLES.glob("*.ja.md")):
        for link in re.findall(r"\]\((/[^)]*)\)", f.read_text(encoding="utf-8")):
            m = re.fullmatch(r"/articles/([^/]+)/", link)
            if m:
                if m.group(1) not in slugs:
                    bad.append((f.name, link, "記事が存在しない"))
            elif link not in STATIC_PATHS:
                bad.append((f.name, link, "未知のパス"))

    for name, link, why in bad:
        print(f"NG {name}: {link}  ({why})", file=sys.stderr)
    if bad:
        print(f"\n壊れた内部リンク {len(bad)}件", file=sys.stderr)
        return 1

    dist_bad = check_dist()
    if dist_bad:
        print("生成物の内部リンクが壊れています:", file=sys.stderr)
        for line in dist_bad[:20]:
            print(f"  NG {line}", file=sys.stderr)
        if len(dist_bad) > 20:
            print(f"  ... 他 {len(dist_bad) - 20}件", file=sys.stderr)
        return 1

    print(f"内部リンク OK（記事{len(slugs)}本 / 生成物も検査済み）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
