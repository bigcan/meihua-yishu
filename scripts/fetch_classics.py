#!/usr/bin/env python3
"""
從 ctext.org 批次下載原典章節並擷取純文本。

用法：
  python fetch_classics.py download <chapter_id> <out_path>   # 下載並擷取單章
  python fetch_classics.py batch                              # 批次下載 v3.1 收錄章節

擷取規則：ctext 章節頁 HTML 內每段文本放在 <td class="ctext">原文</td>。
過濾掉 width: 60px 的行號 cell，只保留正文。
"""

from __future__ import annotations

import html
import os
import re
import sys
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass


BASE_URL = "https://ctext.org/wiki.pl?if=gb&chapter={}"
USER_AGENT = "Mozilla/5.0 (academic mirror; public-domain Qing texts)"


def fetch_html(chapter_id: int | str) -> str:
    url = BASE_URL.format(chapter_id)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_text(raw_html: str) -> list[str]:
    """從 ctext HTML 擷取正文段落"""
    pattern = re.compile(r'<td class="ctext">(.+?)</td>', re.DOTALL)
    blocks = pattern.findall(raw_html)
    out: list[str] = []
    for b in blocks:
        s = re.sub(r"<[^>]+>", "", b)
        s = html.unescape(s).strip()
        if s:
            out.append(s)
    return out


def fetch_chapter(chapter_id: int | str) -> str:
    """下載並回傳純文本（多段以雙換行分隔）"""
    paragraphs = extract_text(fetch_html(chapter_id))
    return "\n\n".join(paragraphs)


# v3.1 收錄章節（chapter_id, 相對檔名, 中文章名）
V3_1_CHAPTERS = [
    # 增刪卜易（完整 5 章）
    (305341, "zengshan-buyi/00-preface.md", "增刪卜易序"),
    (950329, "zengshan-buyi/juan1.md", "增刪卜易卷之一"),
    (157683, "zengshan-buyi/juan2.md", "增刪卜易卷之二"),
    (398174, "zengshan-buyi/juan3.md", "增刪卜易卷之三"),
    (52651,  "zengshan-buyi/juan4.md", "增刪卜易卷之四"),

    # 卜筮正宗（完整 4 章）
    (889452, "buzheng-zhengzong/juan1.md", "卜筮正宗 卷一"),
    (801184, "buzheng-zhengzong/juan2.md", "卜筮正宗 卷二"),
    (944578, "buzheng-zhengzong/juan3.md", "卜筮正宗 卷三"),
    (909268, "buzheng-zhengzong/juan4.md", "卜筮正宗 卷四"),
]


def save_chapter(text: str, out_path: Path, title: str, chapter_id: int | str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        f"# {title}\n\n"
        f"來源：https://ctext.org/wiki.pl?if=gb&chapter={chapter_id}\n"
        f"狀態：原文已下載；現代語譯待補（v3.1 階段）\n\n"
        f"==============================================================\n"
        f"【原文】\n"
        f"==============================================================\n\n"
        f"{text}\n\n"
        f"==============================================================\n"
        f"【現代語譯】\n"
        f"==============================================================\n\n"
        f"_待補。可參考 najia-guide.md / liuyao-yongshen.md 對照閱讀。_\n"
    )
    out_path.write_text(body, encoding="utf-8")


def batch_download(refs_dir: Path) -> None:
    print(f"批次下載 v3.1 章節至 {refs_dir}")
    for chap_id, rel_path, title in V3_1_CHAPTERS:
        out = refs_dir / rel_path
        if out.exists():
            print(f"  · {rel_path} 已存在，略過")
            continue
        print(f"  ↓ fetching #{chap_id} → {rel_path} ...", end=" ", flush=True)
        try:
            text = fetch_chapter(chap_id)
            save_chapter(text, out, title, chap_id)
            print(f"OK ({len(text)} chars)")
        except Exception as e:
            print(f"FAIL: {e}")


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print(__doc__)
        return
    cmd = argv[1]
    if cmd == "download" and len(argv) >= 4:
        chapter_id = argv[2]
        out_path = Path(argv[3])
        text = fetch_chapter(chapter_id)
        save_chapter(text, out_path, f"章節 {chapter_id}", chapter_id)
        print(f"Saved {len(text)} chars to {out_path}")
    elif cmd == "batch":
        refs_dir = Path(__file__).parent.parent / "references" / "classics"
        batch_download(refs_dir)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
