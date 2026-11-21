#!/usr/bin/env python3
"""倪海廈《天紀》易經卦圖透鏡：查某一卦倪師的卜筮用例、爻辭斷訣、卦象、人間道。

    python nihai_lookup.py 22                 # 山火賁：卜筮用例＋爻辭斷訣＋卦象（預設）
    python nihai_lookup.py 22 --kind 人間道   # 只看某一類；--kind all 看全部
    python nihai_lookup.py 22 --max 3         # 每類最多幾條（預設 4）
    python nihai_lookup.py --status           # 語料在哪、哪個 commit、各類覆蓋幾卦

資料來源：nihai-tianji-corpus（https://github.com/Renhuai123/nihai-tianji-corpus，
語料 CC BY-NC-SA 4.0，著作權屬倪海廈先生及其權利繼承人）。本技能**不收錄**語料文字，
只在第一次使用時 clone 到本機快取，執行時即讀即用：
  - 位置：環境變數 NIHAI_CORPUS，否則 ~/.cache/meihua-yishu/nihai-tianji-corpus
  - 沒有快取時自動 `git clone --depth 1`；不能連網就印出指令請使用者手動下載

讀入時的處理（改之前先讀理由）：
1. 取 book=09-hexagrams 的 卦象/卦德、序卦位置、爻辭斷訣、卜筮用例、人間道；
   陽宅與「清扫重挂」（OCR 雜訊多、無卦歸屬）不取。另取別冊中出自分卦影片、講卦圖的
   條目（見 EXTRA：占斷冊「金钱卦」、易理冊「读图」），它們有 gua 欄，歸卦無疑義。
2. 卦序：條目有 gua 欄（六十四卦分卦影片 BV1q7BZYcEZP，part = gua + 3）以 gua 為準；
   沒有才用 h2 在冊中出現的順序（冊內 64 個 h2 依文王卦序排列，test 有核對）。
   原因：語料有 77 條 h2 與 gua 不一致，抽查皆 gua 對（例：h2 歸乾，內容講蠱卦卦圖）。
3. 去重：正片 BV1KJsLekEfA 與分卦影片是同一堂課的兩種剪輯，同一句話常出現兩次，
   而且常只部分重疊。同類之內（跨卦）去標點後 4 字片段重疊 ≥ 60%（以較短者計）視為重複，
   留分卦影片那條：連結直達該卦，卦序也較可靠——正片條目被歸錯卦時就靠這一步認回來。
4. quote 原樣輸出（簡體、口語），不轉繁體、不改字：語料要求原樣引用，
   字幕錯字已由原作者人工裁決並在 note 留痕。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

REPO_URL = "https://github.com/Renhuai123/nihai-tianji-corpus"
DEFAULT_DIR = Path.home() / ".cache" / "meihua-yishu" / "nihai-tianji-corpus"

KINDS = {  # 語料 h3 → 本技能用的類名（順序即輸出順序）
    "卜筮用例": "卜筮用例",
    "爻辞断诀（初爻→上爻）": "爻辭斷訣",
    "卦象 / 卦德": "卦象",
    "序卦位置": "序卦",
    "人间道": "人間道",
}
DEFAULT_KINDS = ["卜筮用例", "爻辭斷訣", "卦象"]
GUA_VIDEO = "BV1q7BZYcEZP"
_PUNCT = re.compile(r"[\s，。、？！：；「」『』“”‘’（）().,!?~～…—\-]+")
_cache: Optional[List[Dict]] = None


def corpus_dir() -> Path:
    return Path(os.environ.get("NIHAI_CORPUS") or DEFAULT_DIR)


def ensure_corpus(clone: bool = True) -> Path:
    d = corpus_dir()
    if (d / "data" / "entries.jsonl").exists():
        return d
    if clone:
        d.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["git", "clone", "--depth", "1", REPO_URL, str(d)],
                           capture_output=True, text=True)
        if r.returncode == 0 and (d / "data" / "entries.jsonl").exists():
            return d
    raise FileNotFoundError(
        f"找不到倪師語料。請手動下載：git clone --depth 1 {REPO_URL} \"{d}\"\n"
        f"（或把已下載的位置設給環境變數 NIHAI_CORPUS）"
    )


def _norm(s: str) -> str:
    return _PUNCT.sub("", s)


def _seconds(t_hms: str) -> int:
    h, m, s = (int(x) for x in t_hms.split(":"))
    return h * 3600 + m * 60 + s


def _grams(s: str, n: int = 4) -> set:
    return {s[i:i + n] for i in range(max(1, len(s) - n + 1))}


DUP_OVERLAP = 0.6  # 兩條 4 字片段重疊佔較短者的比例；同一段話的兩種剪輯常只部分重疊


def _is_dup(a: set, b: set) -> bool:
    return len(a & b) >= DUP_OVERLAP * min(len(a), len(b))


# 六十四卦冊以外、但出自分卦影片（有 gua 欄）且講卦圖的條目，併入對應類
EXTRA = {
    ("10-divination", "金钱卦"): "卜筮用例",   # 賁、剝、小過、既濟的卦圖斷例
    ("08-yili", "二、读图（象）"): "卦象 / 卦德",
}


def _kind_key(e: Dict) -> Optional[str]:
    if e.get("book") == "09-hexagrams":
        if e["h2"] == "清扫重挂" or e["h3"] not in KINDS:
            return None
        return e["h3"]
    if e.get("gua") and (e.get("book"), e.get("h2")) in EXTRA:
        return EXTRA[(e["book"], e["h2"])]
    return None


def parse(entries: List[Dict]) -> List[Dict]:
    """把語料條目整理成本技能用的列（純函式，測試直接餵假資料）。"""
    hexes = [e for e in entries if e.get("book") == "09-hexagrams"]
    order: List[str] = []
    for e in hexes:
        if e["h2"] != "清扫重挂" and e["h2"] not in order:
            order.append(e["h2"])
    rows = []
    for e in entries:
        kind_key = _kind_key(e)
        if kind_key is None:
            continue
        gua = e.get("gua") or order.index(e["h2"]) + 1
        tag = "卦%02d" % e["gua"] if e.get("gua") else "p%02d" % e["part"]
        rows.append({
            "gua": gua,
            "kind": KINDS[kind_key],
            "quote": e["quote"],
            "cite": f"[{tag} §{e['section']} @{e['t_hms']}]",
            "url": f"https://www.bilibili.com/video/{e['bvid']}?p={e['part']}&t={_seconds(e['t_hms'])}",
            "note": e.get("note", ""),
            "_gv": e["bvid"] == GUA_VIDEO,
            "_g": _grams(_norm(e["quote"])),
        })
    # 同類之內跨卦去重：分卦影片版本排前面，重複時留下它（它的卦序來自 gua 欄，較可靠）；
    # 跨卦是因為正片條目只能靠 h2 歸卦，同一段話在正片被歸錯卦時，靠分卦影片的副本認回來。
    rows.sort(key=lambda r: (not r["_gv"], r["gua"]))
    kept: List[Dict] = []
    index: Dict[tuple, List[int]] = {}
    for r in rows:
        cands = set()
        for g in r["_g"]:
            cands.update(index.get((r["kind"], g), ()))
        if any(_is_dup(kept[i]["_g"], r["_g"]) for i in cands):
            continue
        for g in r["_g"]:
            index.setdefault((r["kind"], g), []).append(len(kept))
        kept.append(r)
    for r in kept:
        del r["_gv"], r["_g"]
    kind_order = list(KINDS.values())
    # 輸出順序：卦、類，再以分卦影片優先、依講課時間先後
    kept.sort(key=lambda r: (r["gua"], kind_order.index(r["kind"]), GUA_VIDEO not in r["url"],
                             int(re.search(r"p=(\d+)", r["url"]).group(1)),
                             int(re.search(r"t=(\d+)", r["url"]).group(1))))
    return kept


def load(clone: bool = True) -> List[Dict]:
    global _cache
    if _cache is None:
        d = ensure_corpus(clone)
        with (d / "data" / "entries.jsonl").open(encoding="utf-8") as f:
            _cache = parse([json.loads(line) for line in f])
    return _cache


def lookup(gua: int, kinds: Optional[List[str]] = None, clone: bool = True) -> Dict[str, List[Dict]]:
    kinds = kinds or DEFAULT_KINDS
    out: Dict[str, List[Dict]] = {k: [] for k in kinds}
    for r in load(clone):
        if r["gua"] == gua and r["kind"] in out:
            out[r["kind"]].append(r)
    return out


def _gua_name(gua: int) -> str:
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from meihua_calc import HEXAGRAMS
        return next(name for n, name in HEXAGRAMS.values() if n == gua)
    except Exception:
        return ""


def main(argv: Optional[List[str]] = None) -> int:
    from meihua_calc import configure_stdout
    configure_stdout()
    p = argparse.ArgumentParser(description="倪海廈《天紀》卦圖透鏡查詢")
    p.add_argument("gua", nargs="?", type=int, help="卦序 1–64")
    p.add_argument("--kind", default=None, help="卜筮用例／爻辭斷訣／卦象／序卦／人間道／all")
    p.add_argument("--max", type=int, default=4, help="每類最多幾條（0＝不限）")
    p.add_argument("--status", action="store_true")
    a = p.parse_args(argv)
    try:
        rows = load()
    except FileNotFoundError as e:
        print(e)
        return 1
    if a.status:
        d = corpus_dir()
        commit = subprocess.run(["git", "-C", str(d), "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True).stdout.strip() or "?"
        print(f"語料：{d}（commit {commit}），整理後 {len(rows)} 條")
        for k in KINDS.values():
            covered = {r["gua"] for r in rows if r["kind"] == k}
            print(f"  {k}：{len(covered)}/64 卦，{sum(r['kind'] == k for r in rows)} 條")
        return 0
    if not a.gua or not 1 <= a.gua <= 64:
        p.error("請給卦序 1–64")
    kinds = list(KINDS.values()) if a.kind == "all" else ([a.kind] if a.kind else None)
    if kinds and any(k not in KINDS.values() for k in kinds):
        p.error(f"--kind 只能是 {'／'.join(KINDS.values())} 或 all")
    res = lookup(a.gua, kinds)
    print(f"【倪師《天紀》卦圖透鏡・第{a.gua}卦 {_gua_name(a.gua)}】（補充透鏡，不蓋過爻辭、體用、用神）")
    for k, items in res.items():
        print(f"\n▶ {k}（{len(items)} 條）")
        if not items:
            print("  （倪師課程中未見此卦此類論述）")
        for r in items[: a.max or None]:
            note = f"〔{r['note']}〕" if r["note"] else ""
            print(f"- 「{r['quote']}」{note} {r['cite']}\n  {r['url']}")
        if a.max and len(items) > a.max:
            print(f"  …另 {len(items) - a.max} 條（--max 0 看全部）")
    print("\n出處：倪海廈《天紀》，經 nihai-tianji-corpus 整理（CC BY-NC-SA 4.0）。原話照錄，不改寫。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
