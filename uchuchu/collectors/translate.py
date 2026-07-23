"""翻訳エンジン（3段フォールバック）。

外部の従量課金APIは使わない。優先順位:

  1. claude CLI  … ローカルの Claude Code を叩く。品質が最も高い。
                   API従量課金ではなく Claude Code の契約枠で動く。
                   Mac 上での収集（cron / run.sh）ではこれが使われる。
  2. argostranslate … 完全オフラインの機械翻訳。claude CLI が無い環境
                   （GitHub Actions 等）でのフォールバック。品質は劣る。
  3. 翻訳なし    … どちらも無ければ原文のまま掲載する（サイトは常に動く）。

日→英は argostranslate の品質が公開に耐えないため、
argostranslate 使用時は英→日のみ行う（呼び出し側で制御）。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

# --- 前処理: 訳文を汚すRSS定型文を落とす -------------------------------
_BOILERPLATE = [
    re.compile(r"The post\b.*?appeared first on.*?(?:\.|$)", re.I | re.S),
    re.compile(r"Read this release in English here\.?", re.I),
    re.compile(r"^\s*(?:Description|CONTRACT RELEASE|MEDIA ADVISORY|RELEASE)\s*[:\-]?\s*", re.I),
    re.compile(r"\[\s*(?:…|\.\.\.)\s*\]"),
    re.compile(r"Continue reading.*?(?:\.|$)", re.I),
    re.compile(r"\bClick here\b.*?(?:\.|$)", re.I),
]


def clean_for_translation(text: str) -> str:
    if not text:
        return ""
    out = text
    for pat in _BOILERPLATE:
        out = pat.sub(" ", out)
    return re.sub(r"\s+", " ", out).strip()


# =====================================================================
#  バックエンド 1: claude CLI
# =====================================================================
CLAUDE_BIN = os.environ.get("UCHUCHU_CLAUDE_BIN") or shutil.which("claude")
CLAUDE_BATCH = 12          # 1回のプロンプトに載せる記事数
CLAUDE_TIMEOUT = 240       # 秒

# 翻訳に使うモデル。数百件の定型処理なので軽量モデルで足りる。
# 上位モデルを使うと利用枠を圧迫し、対話側が止まる。
BATCH_MODEL = os.environ.get("UCHUCHU_BATCH_MODEL", "haiku")

_PROMPT = """あなたは宇宙開発分野の専門翻訳者です。
以下のJSONは英語の宇宙関連ニュースです。各記事の title と summary を、
日本語のニュース記事として自然な文体に翻訳してください。

要件:
- title は日本語の報道見出しらしく簡潔に（体言止め・「〜を発表」等を活用）
- summary は敬体（です・ます）ではなく常体（だ・である）に寄せた報道文
- 固有名詞・組織名は日本で一般的な表記に（例: Draper→ドレイパー社、Falcon 9→ファルコン9）
- 専門用語は正確に（lunar lander→月着陸船、payload→搭載物、low Earth orbit→地球低軌道）
- 原文にない情報を足さない。誇張しない。
- 出力は入力と同じキー構造のJSONのみ。前置き・説明・コードフェンスは一切書かない。

入力:
"""


def claude_available() -> bool:
    return bool(CLAUDE_BIN)


def _extract_json(text: str) -> dict | None:
    """CLI出力からJSONオブジェクトを取り出す。"""
    if not text:
        return None
    text = text.strip()
    # コードフェンスが付いた場合を剥がす
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def _claude_call(payload: dict) -> dict | None:
    prompt = _PROMPT + json.dumps(payload, ensure_ascii=False, indent=1)
    try:
        proc = subprocess.run(
            [CLAUDE_BIN, "--model", BATCH_MODEL, "-p", prompt],
            capture_output=True, text=True, timeout=CLAUDE_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"    [claude] 呼び出し失敗: {type(e).__name__}", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(f"    [claude] exit={proc.returncode}: {proc.stderr[:200]}", file=sys.stderr)
        return None
    return _extract_json(proc.stdout)


def translate_items_claude(items: list[dict]) -> int:
    """英語記事リストに title_ja / summary_ja を付与する。付与できた件数を返す。"""
    if not claude_available() or not items:
        return 0
    filled = 0
    for i in range(0, len(items), CLAUDE_BATCH):
        chunk = items[i:i + CLAUDE_BATCH]
        payload = {
            str(n): {
                "title": clean_for_translation(it.get("title", "")),
                "summary": clean_for_translation(it.get("summary", "")),
            }
            for n, it in enumerate(chunk)
        }
        result = _claude_call(payload)
        if not result:
            print(f"    [claude] batch {i // CLAUDE_BATCH + 1} 失敗 — フォールバックへ", file=sys.stderr)
            continue
        for n, it in enumerate(chunk):
            got = result.get(str(n))
            if not isinstance(got, dict):
                continue
            title = (got.get("title") or "").strip()
            summary = (got.get("summary") or "").strip()
            if title and not looks_broken(title):
                # 元要約が字数で切り詰められている場合、訳文も途中で終わるため
                # 省略記号を補って「続きがある」ことを示す。
                if summary and it.get("summary", "").rstrip().endswith("…") \
                        and not summary.endswith(("…", "。", "！", "？")):
                    summary = summary.rstrip("、,.") + "…"
                # 訳文の品質チェック：壊れたテキストなら保存しない
                if not looks_broken(summary):
                    it["title_ja"] = title
                    it["summary_ja"] = summary or it.get("summary_ja") or ""
                    it["translated_ja"] = True
                    filled += 1
                else:
                    print(f"    [claude] ⚠️  {n}: 訳文が破損（品質検査で却下）", file=sys.stderr)
        print(f"    [claude] {min(i + CLAUDE_BATCH, len(items))}/{len(items)} 翻訳済み")
    return filled


def looks_broken(text: str) -> bool:
    """日本語として異常な特徴を検出。破損した翻訳の保存を防ぐ。"""
    if not text:
        return False
    # パターン1: 同じ音の繰り返し（「るるるる」など）
    if re.search(r'([あ-ん])\1{3,}', text):
        return True
    # パターン2: 不自然な長音の繰り返し
    if re.search(r'[゛゜゛゜]{3,}', text):
        return True
    # パターン3: 句読点だけ
    if re.match(r'^[。、！？\s]+$', text):
        return True
    # パターン4: 明らかに翻訳失敗のシグナル語
    if any(sig in text for sig in ['地球が太陽', 'うるるる', 'ッッッ']):
        return True
    return False


# =====================================================================
#  バックエンド 2: argostranslate（完全オフライン）
# =====================================================================
_ENGINE = None
_CHECKED = False

# 機械翻訳が定型的に外す語だけを狙って直す
_GLOSSARY_JA = [
    (re.compile(r"月の?ランダー"), "月着陸船"),
    (re.compile(r"ランダー"), "着陸機"),
    (re.compile(r"月面?着陸ミッションアプリ"), "月着陸ミッション"),
    (re.compile(r"ローバー"), "探査車"),
    (re.compile(r"打ち上げ?パッド"), "発射台"),
    (re.compile(r"ペイロード"), "搭載物"),
    (re.compile(r"軌道船"), "周回機"),
    (re.compile(r"深い宇宙"), "深宇宙"),
    (re.compile(r"低い地球軌道"), "地球低軌道"),
    (re.compile(r"再利用可能な?ロケット"), "再使用ロケット"),
    (re.compile(r"ミッションアプリ"), "ミッション"),
    (re.compile(r"\s*(?:ログイン|投稿|コンテンツ)\s*$"), ""),
    (re.compile(r"^\s*(?:ログイン|投稿|コンテンツ)\s*"), ""),
]


def polish_ja(text: str) -> str:
    if not text:
        return text
    out = text
    for pat, rep in _GLOSSARY_JA:
        out = pat.sub(rep, out)
    return re.sub(r"\s+", " ", out).strip()


def _load_engine():
    global _ENGINE, _CHECKED
    if _CHECKED:
        return _ENGINE
    _CHECKED = True
    try:
        import argostranslate.translate as t
        _ENGINE = t
    except Exception:
        _ENGINE = None
    return _ENGINE


def argos_available() -> bool:
    return _load_engine() is not None


def translate(text: str, from_lang: str, to_lang: str) -> str | None:
    """argostranslate による単文翻訳。未導入・失敗時は None。"""
    if not text or from_lang == to_lang:
        return text or None
    engine = _load_engine()
    if engine is None:
        return None
    src = clean_for_translation(text)
    if not src:
        return None
    try:
        out = engine.translate(src, from_lang, to_lang)
    except Exception:
        return None
    if not out:
        return None
    if to_lang == "ja":
        out = polish_ja(out)
    return out or None


def translate_items_argos(items: list[dict]) -> int:
    """英語記事に title_ja / summary_ja を付ける（オフライン・低品質）。"""
    if not argos_available():
        return 0
    filled = 0
    total = len(items)
    for n, it in enumerate(items, 1):
        title = translate(it.get("title", ""), "en", "ja")
        if title:
            it["title_ja"] = title
            summary = translate(it.get("summary", ""), "en", "ja")
            if summary:
                it["summary_ja"] = summary
            it["translated_ja"] = True
            filled += 1
        if n % 10 == 0 or n == total:
            print(f"    [argos] {n}/{total} 翻訳済み")
    return filled


# =====================================================================
#  公開API
# =====================================================================
def available() -> bool:
    return claude_available() or argos_available()


def backend_name() -> str:
    if claude_available():
        return "claude CLI"
    if argos_available():
        return "argostranslate (offline)"
    return "none"


def translate_english_items(items: list[dict]) -> int:
    """英語記事を日本語化する。使えるバックエンドを順に試す。"""
    if not items:
        return 0
    if claude_available():
        filled = translate_items_claude(items)
        # claude が一部失敗した分だけ argos で埋める
        remaining = [it for it in items if not it.get("translated_ja")]
        if remaining and argos_available():
            print(f"    未翻訳 {len(remaining)}件を argostranslate で補完")
            filled += translate_items_argos(remaining)
        return filled
    return translate_items_argos(items)


def install_models():
    """argostranslate の英⇄日モデルを導入する。"""
    import argostranslate.package as pkg
    pkg.update_package_index()
    wanted = {("en", "ja"), ("ja", "en")}
    installed = 0
    for p in pkg.get_available_packages():
        if (p.from_code, p.to_code) in wanted:
            print(f"installing {p.from_code}->{p.to_code} ...")
            pkg.install_from_path(p.download())
            installed += 1
    print(f"done. installed {installed} model(s).")


if __name__ == "__main__":
    if "--install" in sys.argv:
        install_models()
    else:
        print("backend:", backend_name())
        print("  claude CLI    :", claude_available(), CLAUDE_BIN or "")
        print("  argostranslate:", argos_available())

# --- 訳文の品質チェック --------------------------------------------------
# 機械翻訳（argostranslate）は、金額・単位・固有名詞で崩れることがある。
# 「$ 7.1百万賞を受賞」（$7.1 million award の直訳）が
# トップページの主役記事として出てしまった実例がある。
# 崩れた訳文は載せないほうがよいので、検出して原文に戻す。

_BROKEN_PATTERNS = [
    r"[\$＄]\s*[\d.]+",          # 金額が原文のまま残っている
    r"(?i)\b(million|billion|thousand)\b",   # 単位が訳されていない
    r"[A-Za-z]{4,}\s+[A-Za-z]{4,}\s+[A-Za-z]{4,}",  # 英単語が3語以上連続
]

# 機械翻訳（特に argostranslate）は、同じ語を延々と繰り返す「崩壊」を
# 起こすことがある。「揺るぐるるるるるる」「衛星衛星衛星…」のような出力で、
# 上の英字・金額チェックでは捕まらない。日本語の崩壊を別に検出する。
_JA_DEGEN = [
    re.compile(r"(.)\1{4,}"),        # 同一文字が5回以上連続（るるるるる）
    re.compile(r"(.{2,4}?)\1{2,}"),  # 2〜4字の並びが3回以上連続（衛星衛星衛星）
]


def looks_degenerate_ja(text: str) -> bool:
    """日本語訳が繰り返し崩壊を起こしていれば True。"""
    if not text:
        return False
    return any(p.search(text) for p in _JA_DEGEN)


def looks_broken(text: str) -> bool:
    """訳文が壊れていそうなら True。

    完璧な判定はできないので、**明らかにおかしいものだけ**を弾く。
    弾きすぎると訳文が減って読めなくなるため、条件は絞っている。
    """
    if not text:
        return True
    if looks_degenerate_ja(text):
        return True
    for pat in _BROKEN_PATTERNS:
        if re.search(pat, text):
            return True
    return False


def fix_units(text: str) -> str:
    """金額・単位の直訳を日本語の言い回しに直す。

    翻訳そのものをやり直すより確実で、費用もかからない。
    """
    if not text:
        return text

    def _money(m: "re.Match") -> str:
        v = float(m.group(1))
        unit = m.group(2).lower()
        if unit.startswith("b") or unit == "十億":
            man = v * 100_000        # 10億 = 100,000万
        elif unit.startswith("m") or unit == "百万":
            man = v * 100            # 100万 = 100万
        else:
            return m.group(0)
        # 万で1万を超えるなら億に繰り上げる（「50000万ドル」を避ける）
        if man >= 10_000:
            return f"{man / 10_000:g}億ドル"
        return f"{man:g}万ドル"

    # "$7.1 million" / "$ 7.1百万" の両方に対応する
    text = re.sub(r"[\$＄]\s*([\d.]+)\s*(million|billion|百万|十億)",
                  _money, text, flags=re.I)
    text = re.sub(r"[\$＄]\s*([\d,]+)", lambda m: m.group(1) + "ドル", text)
    # 「award」を「賞」と訳す誤りは、文脈によって
    # 授与する側にも受け取る側にもなるため、機械的には直せない。
    # ここでは直さず、looks_broken で検出して訳し直す。
    return re.sub(r"\s+", " ", text).strip()
