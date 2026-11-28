#!/usr/bin/env python3
"""打ち上げの前日・当日に X へ出す文面を作る（投稿はしない）。

2026-11-28 小嶋さん「やれ」（伸びない原因の調査の手4＝外の入口を1つ作る）。
UchUchU には X のアカウントがまだ無い。アカウントができたら、この文面を
SNS 用の自動操作 Chrome（mini の 9352）から出すジョブを足す。それまでは文面だけ作る。

対象を絞る理由: 世界の打ち上げは週に10本前後あり（SpaceX だけで年100本超）、
全部流すと宣伝の連投になる。日本の打ち上げと有人飛行だけにする。
日付の決まっていない予定（「2027年内」など）は出さない。

    python3 tools/x_launch_posts.py            # 今日（日本時間）の分
    python3 tools/x_launch_posts.py 2027-01-10 # その日の分（前日の告知の確認用）
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from uchuchu import launch_pages  # noqa: E402

JST = timezone(timedelta(hours=9))
SITE = "https://uchuchu.tech"
WDAY = "月火水木金土日"
FUZZY = ("Week", "Month", "Quarter", "Half", "Year")


def is_target(l: dict) -> bool:
    if "JPN" in (l.get("country"), l.get("provider_country")):
        return True
    return (l.get("mission_type") or "") == "Human Exploration"


def post_for(l: dict, kind: str) -> str:
    dt = datetime.fromisoformat(l["net"].replace("Z", "+00:00")).astimezone(JST)
    site = launch_pages._site_meta(l.get("location") or "")["ja"]
    when = f"{dt.month}月{dt.day}日（{WDAY[dt.weekday()]}）"
    exact = (l.get("net_precision") or "") in ("Minute", "Second", "Hour")
    if exact:
        when += f" {dt.hour}:{dt.minute:02d}（日本時間）"
    else:
        when += "・時刻未定"
    head = "【明日打ち上げ】" if kind == "eve" else "【今日打ち上げ】"
    jp = "JPN" in (l.get("country"), l.get("provider_country"))
    url = f"{SITE}/launches/japan/#viewing" if jp else f"{SITE}/launches/"
    tail = "見学場所・中継の案内" if jp else "打ち上げ予定（日本時間）"
    return f"{head}{l['name']}\n{when}\n{site}\n{tail}→ {url}"


def main() -> int:
    day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(JST).date()
    items = json.loads((ROOT / "data/launches.json").read_text(encoding="utf-8")).get("items", [])
    out = []
    for l in items:
        if not l.get("upcoming") or not l.get("net") or not is_target(l):
            continue
        if any(f in (l.get("net_precision") or "") for f in FUZZY):
            continue
        d = datetime.fromisoformat(l["net"].replace("Z", "+00:00")).astimezone(JST).date()
        if d == day:
            out.append(post_for(l, "day"))
        elif d == day + timedelta(days=1):
            out.append(post_for(l, "eve"))
    print("\n\n---\n\n".join(out) if out else "（この日に出す打ち上げはありません）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
