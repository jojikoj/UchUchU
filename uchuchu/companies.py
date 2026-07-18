"""宇宙産業に関わる日本企業のデータベース。

このサイト唯一の「集約でない独自資産」。
ニュース集約は検索エンジンに評価されないが、
どこにも存在しない企業データベースは評価される。
広告（企業掲載枠・タイアップ）の器にもなる。

正確性が生命線なので:
  - 公開情報（各社公式サイト・IR）で確認できることだけ載せる
  - 不確かなことは書かない。空欄のままにする
  - 必ず公式サイトへのリンクを併記し、読者が検証できるようにする
"""
from __future__ import annotations

import json

from . import config

_CACHE: dict | None = None


def _load() -> dict:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    path = config.CONTENT_DIR / "companies.json"
    if not path.exists():
        _CACHE = {"companies": [], "categories": {}}
        return _CACHE
    _CACHE = json.loads(path.read_text(encoding="utf-8"))
    return _CACHE


def all_companies(lang: str = "ja") -> list[dict]:
    """表示用に整形した企業一覧を返す。"""
    data = _load()
    cats = data.get("categories", {})
    out = []
    for c in data.get("companies", []):
        item = dict(c)
        item["display_name"] = c["name"] if lang == "ja" else (c.get("name_en") or c["name"])
        item["sub_name"] = (c.get("name_en") or "") if lang == "ja" else c["name"]
        item["display_summary"] = (
            c.get("summary") if lang == "ja" else (c.get("summary_en") or c.get("summary", ""))
        )
        item["category_labels"] = [
            cats.get(cid, {}).get(lang, cid) for cid in c.get("categories", [])
        ]
        out.append(item)
    out.sort(key=lambda x: x["display_name"])
    return out


def categories(lang: str = "ja") -> list[dict]:
    """カテゴリ一覧（所属企業数つき）。"""
    data = _load()
    cats = data.get("categories", {})
    comps = data.get("companies", [])
    out = []
    for cid, names in cats.items():
        n = sum(1 for c in comps if cid in c.get("categories", []))
        if n:
            out.append({"id": cid, "name": names.get(lang, cid), "count": n})
    out.sort(key=lambda x: -x["count"])
    return out


def by_category(cat_id: str, lang: str = "ja") -> list[dict]:
    return [c for c in all_companies(lang) if cat_id in c.get("categories", [])]


def disclaimer(lang: str = "ja") -> str:
    d = _load().get("_disclaimer", {})
    return d.get(lang, "")


def count() -> int:
    return len(_load().get("companies", []))
