#!/usr/bin/env python3
"""爻辭查詢：由 references/yaoci.md 解析卦辭、384 爻辭與白話。

    python yaoci_lookup.py 21          # 卦辭＋六爻
    python yaoci_lookup.py 21 4        # 噬嗑九四
解卦時直接引用這裡的原文，避免憑記憶寫錯爻辭。
"""
import os
import re
import sys
from typing import Dict, Optional, Tuple

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "yaoci.md")
_POS = {"初": 1, "二": 2, "三": 3, "四": 4, "五": 5, "上": 6}
_cache: Optional[Dict[int, Dict]] = None


def _parse() -> Dict[int, Dict]:
    global _cache
    if _cache is not None:
        return _cache
    data: Dict[int, Dict] = {}
    cur = None
    head = re.compile(r"^第(\d+)卦\s+(\S+)")
    line_re = re.compile(r"^(初[九六]|[九六][二三四五]|上[九六]|用[九六])\s+(\S.*?)\s{1,}(\S.*)$")
    with open(_PATH, encoding="utf-8") as f:
        for raw in f:
            s = raw.strip()
            m = head.match(s)
            if m:
                cur = int(m.group(1))
                data[cur] = {"name": m.group(2), "guaci": "", "yao": {}}
                continue
            if cur is None:
                continue
            if s.startswith("卦辭："):
                data[cur]["guaci"] = s[3:]
                continue
            m = line_re.match(s)
            if m:
                tag, text, plain = m.groups()
                pos = 7 if tag.startswith("用") else _POS[tag[0] if tag[0] in "初上" else tag[1]]
                data[cur]["yao"].setdefault(pos, (tag, text, plain))
    _cache = data
    return data


def get(hex_num: int, pos: Optional[int] = None) -> Dict:
    d = _parse().get(hex_num)
    if not d:
        return {}
    if pos is None:
        return d
    return {"name": d["name"], "guaci": d["guaci"], "line": d["yao"].get(pos)}


def format_line(hex_num: int, pos: int) -> str:
    d = get(hex_num, pos)
    if not d or not d.get("line"):
        return f"（查無第{hex_num}卦第{pos}爻爻辭，請直接查 references/yaoci.md）"
    tag, text, plain = d["line"]
    return f"{d['name']}{tag}：「{text}」——{plain}"


def format_guaci(hex_num: int) -> str:
    d = get(hex_num)
    return f"{d['name']}卦辭：「{d['guaci']}」" if d else ""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    n = int(sys.argv[1])
    if len(sys.argv) > 2:
        print(format_line(n, int(sys.argv[2])))
    else:
        print(format_guaci(n))
        for p in sorted(get(n)["yao"]):
            print("  " + format_line(n, p))
