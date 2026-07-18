"""Flux で UchUchU のイメージ写真を生成する。

対象:
  - 企業DBの6カテゴリ
  - 特集（参入ガイド）記事のカバー
  - 画像のないニュース記事に使う汎用フォールバック

方針:
  - 実在の企業・製品・人物を想起させる指示は書かない（誤認を招くため）
  - 宇宙"ファン"向けの幻想的な絵ではなく、産業・製造の現場感を出す
  - 記事のサムネイルと並ぶので、彩度を上げすぎない

実行:
    python3 tools/gen_flux_images.py            # 未生成のものだけ作る
    python3 tools/gen_flux_images.py --force    # 全部作り直す
"""
from __future__ import annotations

import base64
import os
import pathlib
import sys
import time

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "static" / "img"
ENV = pathlib.Path.home() / "claude_AIR/TOEcompany/製作/adobe-integration/.env"

SUBMIT = "https://api.bfl.ai/v1/flux-pro-1.1"
REALISM = ("realistic, professional photograph, candid, natural lighting, "
           "documentary style, avoid AI art, no text, no logos, no watermark")

JOBS = [
    # --- 企業DB カテゴリ ---
    ("cat-launch.jpg",
     "A large rocket standing on a launch pad at a coastal launch site at dawn, "
     "service tower and umbilical lines visible, engineers in the far distance for scale, "
     "cool blue morning light, wide shot, " + REALISM),
    ("cat-satellite.jpg",
     "Engineers in white cleanroom suits assembling a satellite in a spacecraft "
     "integration cleanroom, gold thermal insulation and solar panels visible, "
     "bright even lighting, industrial and precise, " + REALISM),
    ("cat-component.jpg",
     "Close-up of precision machined metal aerospace components on a workbench in a "
     "Japanese machine shop, CNC lathe blurred in the background, "
     "metal shavings and calipers, warm industrial lighting, " + REALISM),
    ("cat-ground.jpg",
     "A large white parabolic satellite ground station antenna against a clear sky, "
     "seen from below at an angle, steel support structure visible, "
     "clean daylight, " + REALISM),
    ("cat-service.jpg",
     "A mission control room with operators at workstations, large screens showing "
     "world maps and orbital tracks, blue ambient lighting, seen from behind the "
     "operators, " + REALISM),
    ("cat-exploration.jpg",
     "A robotic lunar rover being tested on a simulated regolith surface in a "
     "large indoor test facility, engineers observing at the edge of the frame, "
     "harsh directional lighting simulating sunlight, " + REALISM),

    # --- 特集（参入ガイド）カバー ---
    ("cover-entry.jpg",
     "Interior of a small Japanese metalworking factory, an older craftsman "
     "inspecting a precision metal part under a lamp, lathes and tool cabinets "
     "around, warm practical lighting, sense of craftsmanship, " + REALISM),
    ("cover-quality.jpg",
     "A quality inspector in a clean uniform measuring a metal component with a "
     "coordinate measuring machine, inspection documents and calipers on the bench, "
     "bright neutral factory lighting, " + REALISM),
    ("cover-massprod.jpg",
     "A production line inside a modern factory with rows of identical small "
     "satellite bus panels on assembly trolleys, workers in the background, "
     "clean bright industrial lighting, sense of scale and repetition, " + REALISM),

    # --- ニュース用フォールバック（画像なし記事に使う）---
    ("fallback-space.jpg",
     "A wide shot of a spacecraft assembly hall with a partially assembled "
     "satellite on a stand, cleanroom lighting, engineers small in frame, "
     "calm industrial atmosphere, " + REALISM),
    ("fallback-launch.jpg",
     "A rocket ascending against a clear morning sky seen from a distance, "
     "exhaust plume trailing, minimal ground visible at the bottom, " + REALISM),
    ("fallback-research.jpg",
     "A radio telescope dish array under a clear sky at dusk, several dishes "
     "aligned in the same direction, cool tones, " + REALISM),
# --- 特集記事カバー（第2弾）---
    ("cover-procurement.jpg",
     "A Japanese businessman in a small factory office reviewing printed "
     "technical specification documents at a desk, calipers and a metal part "
     "beside the papers, factory visible through the window behind, "
     "natural daylight, " + REALISM),
    ("cover-materials.jpg",
     "Close-up of engineering material samples laid out on a laboratory bench, "
     "aluminium plates, carbon fibre composite sheets, gold thermal insulation "
     "film and titanium fasteners, neutral studio lighting, shallow depth of field, "
     + REALISM),
    ("cover-market.jpg",
     "A wide view of a modern factory floor with several production cells, "
     "workers at machines in the middle distance, overhead lighting, "
     "sense of an industrial supply chain, " + REALISM),
    ("cover-cost.jpg",
     "A factory owner and an engineer discussing over a laptop and printed "
     "documents at a table in a small manufacturing workshop, machines in the "
     "background, warm natural light, candid working atmosphere, " + REALISM),

    # --- 特集記事カバー（第3弾：入門記事）---
    ("cover-overview.jpg",
     "A wide view of a satellite integration cleanroom seen through an "
     "observation window, several spacecraft structures under assembly, "
     "engineers in white suits working, bright even lighting, "
     "sense of an industry at scale, " + REALISM),
    ("cover-orbit.jpg",
     "A rocket in powered ascent seen from a long distance against a deep "
     "blue sky, the trajectory arcing over rather than going straight up, "
     "thin exhaust trail, curvature of the horizon faintly visible, "
     + REALISM),
]


def api_key() -> str:
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if line.startswith("BFL_API_KEY="):
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                if v:
                    return v
    v = os.environ.get("BFL_API_KEY", "")
    if not v:
        print("BFL_API_KEY が見つかりません", file=sys.stderr)
        raise SystemExit(1)
    return v


def generate(key: str, prompt: str, out: pathlib.Path) -> bool:
    """1枚生成する。submit → polling_url をポーリングして取得する。"""
    try:
        r = requests.post(
            SUBMIT,
            headers={"x-key": key, "Content-Type": "application/json"},
            json={"prompt": prompt, "width": 1024, "height": 576,
                  "prompt_upsampling": False, "safety_tolerance": 2},
            timeout=60)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  submit失敗: {type(e).__name__}: {e}", file=sys.stderr)
        return False

    # レスポンスの polling_url を使う（id からURLを組み立てない）
    poll = data.get("polling_url")
    if not poll:
        print(f"  polling_url なし: {data}", file=sys.stderr)
        return False

    for _ in range(60):
        time.sleep(2)
        try:
            pr = requests.get(poll, headers={"x-key": key}, timeout=30).json()
        except Exception:
            continue
        status = pr.get("status")
        if status == "Ready":
            url = (pr.get("result") or {}).get("sample")
            if not url:
                return False
            img = requests.get(url, timeout=90).content
            out.write_bytes(img)
            return True
        if status in ("Error", "Failed", "Content Moderated",
                      "Request Moderated"):
            print(f"  生成失敗: {status}", file=sys.stderr)
            return False
    print("  タイムアウト", file=sys.stderr)
    return False


def main() -> int:
    force = "--force" in sys.argv
    key = api_key()
    OUT.mkdir(parents=True, exist_ok=True)
    ok = skip = fail = 0
    for name, prompt in JOBS:
        path = OUT / name
        if path.exists() and not force:
            print(f"skip  {name}（既存）")
            skip += 1
            continue
        print(f"生成中 {name} ...")
        if generate(key, prompt, path):
            print(f"  ✅ {path.stat().st_size // 1024}KB")
            ok += 1
        else:
            fail += 1
    print(f"\n=== 生成{ok} / スキップ{skip} / 失敗{fail} ===")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
