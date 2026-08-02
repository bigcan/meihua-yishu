#!/usr/bin/env python3
"""
Tier 8：安裝包（Cowork / claude.ai 上傳檔）

前七層測的是技能算得對、輸出拿得到；本層測的是「裝不裝得起來」。這層的失敗
模式全部是靜默的——技能照樣出現在清單裡，只是永遠不被觸發，或引用的檔案不在
包裡，使用者只會覺得「怎麼不準」。

驗證項目：
  1. frontmatter 必須是合法 YAML
     —— 迴歸測試：description 內含「Triggers on: 」這種「冒號+空格」，未加引號
        的 YAML 純量會整段解析失敗，技能載入時 metadata 全空（觸發詞一個都不算數）
  2. plugin.json / marketplace.json 與 SKILL.md 的 name 三者一致
  3. 打包用的 description 不得超過 claude.ai 的 200 字元上限
  4. 兩種包的目錄結構（Cowork 要 skills/<name>/，claude.ai 要 <name>/）
  5. 包裡不得有測試檔／__pycache__；SKILL.md 引用的 references 一個都不能少
  6. 解開後的 scripts 仍可獨立執行
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_package import (  # noqa: E402
    CLAUDE_AI_DESCRIPTION_LIMIT,
    PACKAGED_DESCRIPTION,
    REPO_ROOT,
    SKILL_NAME,
    build,
    packaged_skill_md,
)

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def split_frontmatter(text: str) -> str:
    match = FRONTMATTER_RE.match(text)
    if match is None:
        raise AssertionError("SKILL.md 沒有 YAML frontmatter")
    return match.group(1)


def scalar_fields(frontmatter: str) -> dict[str, str]:
    """不靠 pyyaml 取出單行 key: value（本 repo 的 frontmatter 只有純量欄位）。"""
    fields = {}
    for line in frontmatter.splitlines():
        match = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


class TestFrontmatterIsValidYaml(unittest.TestCase):
    """description 一旦解析失敗，技能會「載入但永不觸發」，且沒有任何錯誤訊息。"""

    def assert_no_bare_colon_scalar(self, frontmatter: str, label: str) -> None:
        for key, raw in scalar_fields(frontmatter).items():
            if raw and raw[0] in "'\"|>[{":
                continue  # 有引號或區塊/流式標記，冒號合法
            self.assertNotIn(
                ": ",
                raw,
                f"{label} 的 {key} 是未加引號的 YAML 純量卻含「冒號+空格」，"
                "整段 frontmatter 會解析失敗（metadata 全空）。請加單引號。",
            )

    def test_repo_skill_md_frontmatter(self):
        text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assert_no_bare_colon_scalar(split_frontmatter(text), "SKILL.md")

    def test_packaged_skill_md_frontmatter(self):
        self.assert_no_bare_colon_scalar(
            split_frontmatter(packaged_skill_md()), "打包後的 SKILL.md"
        )

    def test_parses_with_pyyaml_when_available(self):
        try:
            import yaml  # noqa: PLC0415
        except ImportError:
            self.skipTest("未安裝 pyyaml（非核心依賴，僅作額外驗證）")

        for label, text in (
            ("SKILL.md", (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")),
            ("打包後的 SKILL.md", packaged_skill_md()),
        ):
            with self.subTest(label=label):
                data = yaml.safe_load(split_frontmatter(text))
                self.assertEqual(data["name"], SKILL_NAME)
                self.assertTrue(data["description"].strip(), "description 不得為空")


class TestManifestsAgree(unittest.TestCase):
    """三份檔案各寫一次 name，任何一份漂掉都會讓安裝出來的技能對不上。"""

    def setUp(self):
        self.plugin = json.loads(
            (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.marketplace = json.loads(
            (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        self.skill_fields = scalar_fields(
            split_frontmatter((REPO_ROOT / "SKILL.md").read_text(encoding="utf-8"))
        )

    def test_name_matches_everywhere(self):
        self.assertEqual(self.plugin["name"], SKILL_NAME)
        self.assertEqual(unquote(self.skill_fields["name"]), SKILL_NAME)
        entries = [p for p in self.marketplace["plugins"] if p["name"] == SKILL_NAME]
        self.assertEqual(len(entries), 1, "marketplace.json 必須恰有一筆本外掛的項目")
        self.assertEqual(entries[0]["source"], "./", "本 repo 自身就是外掛來源")

    def test_version_is_semver(self):
        self.assertRegex(self.plugin.get("version", ""), r"^\d+\.\d+\.\d+$")


class TestPackagedDescription(unittest.TestCase):
    def test_within_claude_ai_limit(self):
        self.assertLessEqual(
            len(PACKAGED_DESCRIPTION),
            CLAUDE_AI_DESCRIPTION_LIMIT,
            "claude.ai 上傳技能的 description 上限 200 字元，超過會被拒絕",
        )

    def test_packaged_skill_md_uses_it(self):
        fields = scalar_fields(split_frontmatter(packaged_skill_md()))
        self.assertEqual(unquote(fields["description"]), PACKAGED_DESCRIPTION)

    def test_body_is_untouched(self):
        """打包只准動 description 那一行，其餘一字不改。"""
        repo_lines = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8").splitlines()
        packaged_lines = packaged_skill_md().splitlines()
        self.assertEqual(len(repo_lines), len(packaged_lines))
        differing = [
            i for i, (a, b) in enumerate(zip(repo_lines, packaged_lines)) if a != b
        ]
        self.assertEqual(len(differing), 1, "只應有 description 一行不同")
        self.assertTrue(packaged_lines[differing[0]].startswith("description:"))


class TestPackageLayout(unittest.TestCase):
    """兩種包的結構不同，弄反了上傳會被拒或技能不出現。"""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.built = build(Path(cls._tmp.name))
        cls.plugin_names = zipfile.ZipFile(cls.built["plugin_zip"]).namelist()
        cls.skill_names = zipfile.ZipFile(cls.built["skill_zip"]).namelist()

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_plugin_layout(self):
        # Cowork 認 zip 根目錄即 plugin 根，技能在 skills/<name>/
        self.assertIn(".claude-plugin/plugin.json", self.plugin_names)
        self.assertIn(f"skills/{SKILL_NAME}/SKILL.md", self.plugin_names)
        self.assertNotIn("SKILL.md", self.plugin_names)

    def test_skill_layout(self):
        # claude.ai 要求 zip 內含一層與 name 同名的資料夾
        self.assertIn(f"{SKILL_NAME}/SKILL.md", self.skill_names)
        for name in self.skill_names:
            self.assertTrue(
                name.startswith(f"{SKILL_NAME}/"),
                f"{name} 不在 {SKILL_NAME}/ 底下，claude.ai 會拒絕這種結構",
            )

    def test_plugin_and_dot_plugin_are_identical(self):
        self.assertEqual(
            self.built["plugin_zip"].read_bytes(),
            self.built["plugin_file"].read_bytes(),
            "兩個副檔名只是為了相容不同上傳對話框，內容必須一致",
        )

    def test_no_dev_files_shipped(self):
        for names in (self.plugin_names, self.skill_names):
            for name in names:
                base = os.path.basename(name)
                self.assertFalse(base.startswith("test_"), f"包裡不該有測試檔 {name}")
                self.assertNotIn("__pycache__", name)
                self.assertNotEqual(base, "build_package.py")

    def test_referenced_files_are_present(self):
        """SKILL.md 引用的 references 若沒進包，解卦時就是斷鏈。"""
        skill_text = (REPO_ROOT / "SKILL.md").read_text(encoding="utf-8")
        referenced = set(re.findall(r"references/([\w./-]+\.md)", skill_text))
        self.assertTrue(referenced, "SKILL.md 應該引用到 references/")
        for names, prefix in (
            (self.plugin_names, f"skills/{SKILL_NAME}"),
            (self.skill_names, SKILL_NAME),
        ):
            for ref in sorted(referenced):
                self.assertIn(f"{prefix}/references/{ref}", names)

    def test_ethics_travels_with_the_skill(self):
        # SKILL.md 尾段寫「完整倫理規範見專案根目錄 ETHICS.md」，對技能而言
        # 「根」就是技能資料夾，所以兩份 ETHICS 必須放在 SKILL.md 旁邊
        self.assertIn(f"skills/{SKILL_NAME}/ETHICS.md", self.plugin_names)
        self.assertIn(f"{SKILL_NAME}/ETHICS.zh-TW.md", self.skill_names)

    def test_extracted_scripts_still_run(self):
        with tempfile.TemporaryDirectory() as extract_dir:
            zipfile.ZipFile(self.built["skill_zip"]).extractall(extract_dir)
            skill_dir = Path(extract_dir) / SKILL_NAME
            result = subprocess.run(
                [sys.executable, "scripts/meihua_calc.py", "num", "6", "8", "9"],
                cwd=skill_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("本卦", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
