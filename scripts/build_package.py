#!/usr/bin/env python3
"""把這個 repo 打包成 Claude 可安裝的兩種格式。

repo 根目錄本身就是一個 skill（SKILL.md 在根），也是一個 plugin
（.claude-plugin/plugin.json）。Claude Code 兩種都吃，但 Cowork 與 claude.ai
只吃「上傳檔」，而且兩者要的目錄結構不同：

  meihua-yishu.plugin / .zip   Cowork「上傳外掛」用。zip 根目錄 = plugin 根，
                               技能放在 skills/meihua-yishu/（Cowork UI 以
                               skills/*/SKILL.md 列出技能分頁）。
  meihua-yishu-skill.zip       claude.ai Settings > Capabilities > Skills 用。
                               zip 內必須有一層與 name 同名的資料夾。

description 覆寫：claude.ai 對 skill description 有 200 字元上限，repo 內
SKILL.md 的 description 是 274 字元（觸發詞列得比較全，Claude Code 用）。
打包時統一換成下面的 PACKAGED_DESCRIPTION，兩個包一致，避免同一個人裝在
Cowork 與 chat 兩邊觸發行為不同。改觸發詞請改這裡，別改 SKILL.md。

用法：
    python scripts/build_package.py              # 輸出到 dist/
    python scripts/build_package.py --out /tmp   # 輸出到指定目錄
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from meihua_calc import configure_stdout  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "meihua-yishu"

# claude.ai 上限 200 字元，build 時會斷言。CJK 一個字算一個字元。
PACKAGED_DESCRIPTION = (
    "梅花易數 + 金錢卦/納甲（六爻）雙系統占卜起卦解卦。"
    "Triggers: 占卜, 算卦, 問卦, 起卦, 解卦, 測字, 拆字, 金錢卦, 六爻, 納甲, 用神, "
    "meihua, plum blossom, I Ching divination."
)
CLAUDE_AI_DESCRIPTION_LIMIT = 200

# zip 內時間戳固定，重跑 build 產出位元組相同（方便比對是否真的變了）
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

# 技能資料夾內容：SKILL.md 用相對路徑引用 references/ 與 scripts/，
# 第 467 行還引用「專案根目錄 ETHICS.md」——對技能而言根就是技能資料夾，
# 所以 ETHICS 兩份要跟著進來，否則包裝後是斷鏈。
SKILL_FILES = ["SKILL.md", "ETHICS.md", "ETHICS.zh-TW.md", "LICENSE"]
SKILL_DIRS = ["references", "scripts"]

# plugin 根（技能資料夾之外）另外附的檔案
PLUGIN_ROOT_FILES = ["README.md", "README.zh-TW.md", "LICENSE"]

EXCLUDED_SCRIPTS = {"build_package.py"}
EXCLUDED_SCRIPT_PREFIXES = ("test_",)


def packaged_skill_md() -> str:
    """讀 SKILL.md，只換掉 frontmatter 的 description，其餘一字不動。"""
    text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"(---\n)(.*?\n)(---\n)", text, re.DOTALL)
    if match is None:
        raise SystemExit("SKILL.md 缺少 YAML frontmatter，無法打包")

    frontmatter = match.group(2)
    if not re.search(r"^description:.*$", frontmatter, re.MULTILINE):
        raise SystemExit("SKILL.md frontmatter 沒有 description 欄位")

    # 一定要加引號：description 裡有「Triggers: 」這種「冒號+空格」，YAML 純量
    # 不加引號會整段 frontmatter 解析失敗，技能載入時 metadata 全空（沒有觸發詞）。
    new_frontmatter = re.sub(
        r"^description:.*$",
        f"description: '{PACKAGED_DESCRIPTION}'",
        frontmatter,
        count=1,
        flags=re.MULTILINE,
    )
    return match.group(1) + new_frontmatter + match.group(3) + text[match.end() :]


def _is_shippable(path: Path) -> bool:
    if "__pycache__" in path.parts or path.name == ".DS_Store":
        return False
    if path.suffix in {".pyc", ".pyo"}:
        return False
    if path.parent.name == "scripts":
        if path.name in EXCLUDED_SCRIPTS:
            return False
        if path.name.startswith(EXCLUDED_SCRIPT_PREFIXES):
            return False
    return True


def collect_skill_entries(prefix: str) -> list[tuple[str, bytes]]:
    """技能資料夾的 (zip 內路徑, 內容)，路徑排序後回傳。"""
    entries: list[tuple[str, bytes]] = []

    for name in SKILL_FILES:
        source = REPO_ROOT / name
        if not source.exists():
            raise SystemExit(f"缺少 {name}，無法打包")
        data = (
            packaged_skill_md().encode("utf-8")
            if name == "SKILL.md"
            else source.read_bytes()
        )
        entries.append((f"{prefix}/{name}", data))

    for dirname in SKILL_DIRS:
        source_dir = REPO_ROOT / dirname
        if not source_dir.is_dir():
            raise SystemExit(f"缺少 {dirname}/，無法打包")
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file() or not _is_shippable(path):
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            entries.append((f"{prefix}/{rel}", path.read_bytes()))

    return sorted(entries)


def collect_plugin_entries() -> list[tuple[str, bytes]]:
    """plugin 包：zip 根 = plugin 根，技能在 skills/<name>/。"""
    entries = [
        (
            ".claude-plugin/plugin.json",
            (REPO_ROOT / ".claude-plugin" / "plugin.json").read_bytes(),
        )
    ]
    for name in PLUGIN_ROOT_FILES:
        source = REPO_ROOT / name
        if source.exists():
            entries.append((name, source.read_bytes()))
    entries.extend(collect_skill_entries(f"skills/{SKILL_NAME}"))
    return sorted(entries)


def write_zip(target: Path, entries: list[tuple[str, bytes]]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for arcname, data in entries:
            info = zipfile.ZipInfo(arcname, date_time=FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)


def build(out_dir: Path) -> dict[str, Path]:
    if len(PACKAGED_DESCRIPTION) > CLAUDE_AI_DESCRIPTION_LIMIT:
        raise SystemExit(
            f"PACKAGED_DESCRIPTION 長度 {len(PACKAGED_DESCRIPTION)} 超過 "
            f"claude.ai 上限 {CLAUDE_AI_DESCRIPTION_LIMIT}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    plugin_zip = out_dir / f"{SKILL_NAME}.zip"
    plugin_file = out_dir / f"{SKILL_NAME}.plugin"
    skill_zip = out_dir / f"{SKILL_NAME}-skill.zip"

    write_zip(plugin_zip, collect_plugin_entries())
    # 同一份位元組兩個副檔名：桌面版上傳對話框只收 .zip，Cowork 的外掛預覽
    # 認 .plugin（anthropics/claude-code#28337）。
    shutil.copyfile(plugin_zip, plugin_file)
    write_zip(skill_zip, collect_skill_entries(SKILL_NAME))

    return {"plugin_zip": plugin_zip, "plugin_file": plugin_file, "skill_zip": skill_zip}


def main() -> int:
    configure_stdout()
    parser = argparse.ArgumentParser(description="打包 meihua-yishu 供 Cowork / claude.ai 安裝")
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "dist"),
        help="輸出目錄（預設 dist/）",
    )
    args = parser.parse_args()

    built = build(Path(args.out).resolve())
    print(f"description ({len(PACKAGED_DESCRIPTION)}/{CLAUDE_AI_DESCRIPTION_LIMIT} chars) OK")
    for label, path in built.items():
        size_kb = path.stat().st_size / 1024
        print(f"{label:12s} {path}  ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
