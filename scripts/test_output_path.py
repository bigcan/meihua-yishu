#!/usr/bin/env python3
"""
Tier 7：輸出路徑與擲卦入口

前六層測的是「算得對不對」，本層測的是「使用者實際拿不拿得到」。稽核發現
print_result / print_strategy_advice / get_hexagram_strategy / get_position_risk
與 jinqian_gua 的擲卦入口從未被任何測試執行過——策略區塊是 CLAUDE.md 明定的
必出輸出，擲卦是金錢卦的唯一入口，兩者卻都沒有跑過的測試護欄。

驗證項目：
  1. CLI 在受限編碼主控台（cp950/cp437/ascii）不得崩潰
     —— 迴歸測試：📿/⚠️ 曾使 Windows cp950 主控台整份結果中斷（UnicodeEncodeError）
  2. print_result / print_strategy_advice 全策略型別冒煙測試
  3. get_hexagram_strategy / get_position_risk 契約
  4. jinqian_gua 擲卦入口：銅錢值域、六爻、種子決定性、6/7/8/9 分布
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jinqian_gua import (  # noqa: E402
    YAO_TYPES,
    random_hexagram,
    throw_one_yao,
)
from meihua_calc import (  # noqa: E402
    HEXAGRAM_STRATEGY,
    STRATEGY_NEXT_STEPS,
    get_hexagram_strategy,
    get_position_risk,
    print_result,
    print_strategy_advice,
    qigua_by_numbers,
)

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================================
# 1. 受限編碼主控台
# ============================================================================
class TestRestrictedEncodingConsole(unittest.TestCase):
    """Windows 主控台預設 cp950/cp437 無法編碼 📿⚠️，未處理則 UnicodeEncodeError
    會中斷整份起卦結果。三個 CLI 入口都必須在最壞情況（ascii）下仍完整輸出。"""

    CASES = [
        ("meihua_calc.py", ["num", "6", "8"]),
        ("meihua_calc.py", ["lunar", "2024", "6", "15", "23"]),
        ("meihua_calc.py", ["gregorian", "2024", "1", "18", "14"]),
        ("jinqian_gua.py", ["random"]),
    ]
    ENCODINGS = ["cp950", "cp437", "ascii"]

    def _run(self, script: str, args: list[str], encoding: str):
        env = dict(os.environ, PYTHONIOENCODING=encoding)
        return subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, script), *args],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=env, timeout=60)

    def test_cli_survives_restricted_encoding(self):
        for script, args in self.CASES:
            for enc in self.ENCODINGS:
                with self.subTest(script=script, args=args, encoding=enc):
                    r = self._run(script, args, enc)
                    self.assertEqual(
                        r.returncode, 0,
                        f"{script} {' '.join(args)} 於 {enc} 主控台崩潰：\n{r.stderr}")
                    self.assertNotIn("UnicodeEncodeError", r.stderr)

    def test_output_not_truncated_by_encoding(self):
        """崩潰若發生在 print_result 中途，前半段仍會印出——因此不能只看 returncode，
        要確認最後一段（變卦）確實抵達。"""
        r = self._run("meihua_calc.py", ["num", "6", "8"], "cp950")
        self.assertIn("變卦", r.stdout)


# ============================================================================
# 2. 輸出函式冒煙測試
# ============================================================================
class TestPrintPaths(unittest.TestCase):
    """print_* 從未被執行過。至少要保證每種策略型別都印得出來、不拋例外。"""

    def test_print_result_runs_for_every_strategy_type(self):
        seen = set()
        for num1 in range(1, 9):
            for num2 in range(1, 9):
                result = qigua_by_numbers(num1, num2)
                typ = HEXAGRAM_STRATEGY[result["本卦"]["序號"]][0]
                seen.add(typ)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    print_result(result)
                self.assertIn("本卦", buf.getvalue())
        self.assertGreaterEqual(
            len(seen), 4, f"64 種數字組合應涵蓋多種策略型別，實得 {seen}")

    def test_print_result_covers_hu_from_bian_branch(self):
        """乾/坤的互卦註記走的是 print_result 另一條分支；解卦時必須明言互卦
        係取自變卦，所以這行註記本身就是輸出契約的一部分。"""
        buf = io.StringIO()
        with redirect_stdout(buf):
            print_result(qigua_by_numbers(8, 8))
        self.assertIn("改從變卦取互", buf.getvalue())

    def test_print_result_omits_hu_note_for_ordinary_gua(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            print_result(qigua_by_numbers(6, 8))
        self.assertNotIn("改從變卦取互", buf.getvalue())

    def test_print_strategy_advice_emits_next_step(self):
        """每個策略碼都必須輸出對應的【下一步】——SKILL.md 明定不可省略"""
        by_advice = {}
        for num, (_typ, advice, _jr, _path) in HEXAGRAM_STRATEGY.items():
            by_advice.setdefault(advice, num)
        self.assertEqual(set(by_advice), set(STRATEGY_NEXT_STEPS),
                         "策略碼與【下一步】對照表不一致")
        for advice, num in by_advice.items():
            with self.subTest(advice=advice, hexagram=num):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    print_strategy_advice(num)
                out = buf.getvalue()
                self.assertIn("【策略建議】", out)
                self.assertIn(STRATEGY_NEXT_STEPS[advice], out)

    def test_strategy_block_carries_all_mandatory_fields(self):
        """CLAUDE.md 明定必出欄位：類型／策略／爻辭吉語比例／變卦路徑。
        缺任一欄即為輸出契約破損（先前刪掉整行比例也沒有測試會紅）。"""
        num = 7  # 師：排斥子・走，有變卦路徑
        typ, advice, rate, path = HEXAGRAM_STRATEGY[num]
        buf = io.StringIO()
        with redirect_stdout(buf):
            print_strategy_advice(num)
        out = buf.getvalue()
        self.assertIn(f"類型：{typ}", out)
        self.assertIn(f"建議：{advice}", out)
        self.assertIn(f"{rate}%", out)
        self.assertIn(path, out)

    def test_rate_is_labelled_as_text_metric_not_jilv(self):
        """爻辭吉語比例是文本指標，不得以「吉率」之名輸出——會被讀成成功機率。"""
        buf = io.StringIO()
        with redirect_stdout(buf):
            print_strategy_advice(7)
        out = buf.getvalue()
        self.assertIn("爻辭吉語比例", out)
        self.assertIn("非成功機率", out)
        self.assertNotIn("吉率", out)


# ============================================================================
# 2b. STRATEGY_NEXT_STEPS ↔ SKILL.md 下一步對照表
# ============================================================================
class TestNextStepsMatchSkillMd(unittest.TestCase):
    """SKILL.md 的【下一步】表是給 Claude 照抄的，程式輸出的是同一份文字。
    兩邊各存一份就會漂移——而「印出來的字等於字典裡的字」是循環驗證，
    抓不到字典本身被改。此測試把字典釘在 SKILL.md 上。"""

    SKILL_MD = os.path.join(SCRIPTS_DIR, "..", "SKILL.md")

    def test_next_steps_in_sync_with_skill_md(self):
        import re
        with open(self.SKILL_MD, encoding="utf-8") as fh:
            text = fh.read()
        md = dict(re.findall(r"^([留走守變慎觀])\|(.+?)\s*$", text, re.M))
        self.assertEqual(
            set(md), set(STRATEGY_NEXT_STEPS),
            f"SKILL.md 下一步表與 STRATEGY_NEXT_STEPS 策略碼不一致："
            f"md−code={set(md) - set(STRATEGY_NEXT_STEPS)} "
            f"code−md={set(STRATEGY_NEXT_STEPS) - set(md)}")
        for code, md_text in md.items():
            with self.subTest(策略=code):
                self.assertEqual(
                    STRATEGY_NEXT_STEPS[code], f"【下一步】{md_text}",
                    f"策略「{code}」的下一步文字不同步：\n"
                    f"  SKILL.md: {md_text}\n"
                    f"  程式碼   : {STRATEGY_NEXT_STEPS[code]}")


# ============================================================================
# 3. 策略存取函式契約
# ============================================================================
class TestStrategyAccessors(unittest.TestCase):
    """測試過去只直讀 HEXAGRAM_STRATEGY 字典，繞過了真正組裝必出區塊的這兩個函式。"""

    def test_get_hexagram_strategy_matches_table(self):
        for num, (typ, advice, jr, path) in HEXAGRAM_STRATEGY.items():
            with self.subTest(hexagram=num):
                got = get_hexagram_strategy(num)
                self.assertEqual(
                    got, {"type": typ, "advice": advice,
                          "ji_rate": jr, "change_path": path})

    def test_get_hexagram_strategy_out_of_range(self):
        for bad in (0, 65, -1, 999):
            self.assertIsNone(get_hexagram_strategy(bad))

    def test_position_risk_covers_all_positions(self):
        levels = set()
        for pos in range(1, 7):
            for is_yang in (True, False):
                with self.subTest(position=pos, is_yang=is_yang):
                    risk = get_position_risk(pos, is_yang)
                    self.assertEqual(set(risk), {"coefficient", "risk_level", "warning"})
                    levels.add(risk["risk_level"])
        self.assertTrue({"高風險", "最佳", "佳"}.issubset(levels), levels)

    def test_yang_third_position_is_flagged_high_risk(self):
        risk = get_position_risk(3, is_yang=True)
        self.assertEqual(risk["risk_level"], "高風險")
        self.assertIsNotNone(risk["warning"])

    def test_fifth_position_never_warns(self):
        for is_yang in (True, False):
            self.assertIsNone(get_position_risk(5, is_yang)["warning"])


# ============================================================================
# 4. 金錢卦擲卦入口
# ============================================================================
class TestCoinCasting(unittest.TestCase):
    """random_hexagram / throw_one_yao 是金錢卦的唯一入口，先前 0 覆蓋。"""

    def test_throw_one_yao_domain(self):
        import random as _random
        rng = _random.Random(20260802)
        for _ in range(500):
            coins = throw_one_yao(rng)
            self.assertEqual(len(coins), 3)
            for c in coins:
                self.assertIn(c, (2, 3), "銅錢只能是 2(字/陰) 或 3(背/陽)")

    def test_random_hexagram_shape(self):
        hexagram = random_hexagram(seed=42)
        self.assertEqual(len(hexagram.yaos), 6)
        self.assertEqual([y.position for y in hexagram.yaos], [1, 2, 3, 4, 5, 6],
                         "爻位須自下而上 1..6")
        for y in hexagram.yaos:
            self.assertIn(y.total, (6, 7, 8, 9))

    def test_random_hexagram_is_seed_deterministic(self):
        a = random_hexagram(seed=12345)
        b = random_hexagram(seed=12345)
        c = random_hexagram(seed=54321)
        self.assertEqual([y.coins for y in a.yaos], [y.coins for y in b.yaos])
        self.assertNotEqual([y.coins for y in a.yaos], [y.coins for y in c.yaos])

    def test_three_coin_distribution(self):
        """三枚銅錢法：老陰6=1/8、少陽7=3/8、少陰8=3/8、老陽9=1/8。
        偏離即代表銅錢值域或擲法被改動（例：誤用大衍法比例）。"""
        counts = {6: 0, 7: 0, 8: 0, 9: 0}
        n = 24000
        for i in range(n):
            for y in random_hexagram(seed=i).yaos:
                counts[y.total] += 1
        total = sum(counts.values())
        expected = {6: 1 / 8, 7: 3 / 8, 8: 3 / 8, 9: 1 / 8}
        for k, exp in expected.items():
            with self.subTest(total=k, name=YAO_TYPES[k][0]):
                self.assertAlmostEqual(
                    counts[k] / total, exp, delta=0.015,
                    msg=f"{k}({YAO_TYPES[k][0]}) 佔比 {counts[k] / total:.4f}，"
                        f"三錢法應為 {exp}")

    def test_changing_lines_match_yao_types(self):
        """6/9 為老陰老陽（動），7/8 為少陽少陰（不動）"""
        for i in range(200):
            for y in random_hexagram(seed=i).yaos:
                self.assertEqual(y.is_changing, y.total in (6, 9))
                self.assertEqual(y.is_yang, y.total in (7, 9))


if __name__ == "__main__":
    unittest.main(verbosity=2)
