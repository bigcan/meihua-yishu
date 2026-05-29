#!/usr/bin/env python3
"""
Tier 6：梅花易數起卦端到端單元測試

驗證項目：
  1. num_to_gua / num_to_yao 餘 0 邊界（餘 0 當 8 / 餘 0 當 6）
  2. qigua_by_numbers：兩數起卦、三數起卦（指定動爻）
  3. qigua_by_time：邵子《梅花易數》觀梅占經典案例
     - 辰年十二月十七日申時 → 澤火革，初爻動，互天風姤，變澤山咸
     - 體兌金，用離火，火剋金 = 用剋體（凶）
  4. qigua_by_gregorian_time：西曆→農曆→起卦端到端
  5. 體用判定方向（動爻 ≤ 3 上為體；> 3 下為體）

整條梅花起卦線（時間/數字/西曆）與已驗證的農曆+八卦+動爻數整合驗證。
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from meihua_calc import (  # noqa: E402
    num_to_gua,
    num_to_yao,
    qigua_by_gregorian_time,
    qigua_by_numbers,
    qigua_by_time,
)


# ============================================================================
# 1. num_to_gua / num_to_yao 邊界
# ============================================================================
class TestNumToGuaYao(unittest.TestCase):
    """餘 0 應當 8（卦）/ 6（爻），不可返回 0"""

    def test_gua_boundary_zero_becomes_eight(self):
        self.assertEqual(num_to_gua(8), 8)
        self.assertEqual(num_to_gua(16), 8)
        self.assertEqual(num_to_gua(24), 8)
        self.assertEqual(num_to_gua(80), 8)

    def test_gua_normal_range(self):
        for n in range(1, 9):
            self.assertEqual(num_to_gua(n), n)

    def test_gua_wraparound(self):
        for n in range(1, 8):
            self.assertEqual(num_to_gua(n + 8), n)
            self.assertEqual(num_to_gua(n + 16), n)

    def test_yao_boundary_zero_becomes_six(self):
        self.assertEqual(num_to_yao(6), 6)
        self.assertEqual(num_to_yao(12), 6)
        self.assertEqual(num_to_yao(60), 6)

    def test_yao_normal_range(self):
        for n in range(1, 7):
            self.assertEqual(num_to_yao(n), n)


# ============================================================================
# 2. qigua_by_numbers
# ============================================================================
class TestQiguaByNumbers(unittest.TestCase):

    def test_two_numbers_water_earth(self):
        """6, 8 → 上坎(6) 下坤(8) = 水地比，動爻 = (6+8)%6 = 2"""
        result = qigua_by_numbers(6, 8)
        self.assertEqual(result["本卦"]["名稱"], "水地比")
        self.assertEqual(result["本卦"]["序號"], 8)
        self.assertTrue(result["本卦"]["上卦"].startswith("坎"))
        self.assertTrue(result["本卦"]["下卦"].startswith("坤"))
        self.assertEqual(result["本卦"]["動爻"], "第2爻")

    def test_three_numbers_explicit_dong(self):
        """6, 8, 3 → 上坎下坤，動爻 = 3"""
        result = qigua_by_numbers(6, 8, 3)
        self.assertEqual(result["本卦"]["名稱"], "水地比")
        self.assertEqual(result["本卦"]["動爻"], "第3爻")

    def test_pure_qian(self):
        """1, 1 → 上乾下乾 = 乾為天"""
        result = qigua_by_numbers(1, 1)
        self.assertEqual(result["本卦"]["名稱"], "乾為天")
        self.assertEqual(result["本卦"]["動爻"], "第2爻")  # (1+1)%6 = 2

    def test_pure_kun(self):
        """8, 8 → 上坤下坤 = 坤為地"""
        result = qigua_by_numbers(8, 8)
        self.assertEqual(result["本卦"]["名稱"], "坤為地")
        self.assertEqual(result["本卦"]["動爻"], "第4爻")  # (8+8)%6 = 4


# ============================================================================
# 3. 邵子觀梅占（《梅花易數》最著名案例）
# ============================================================================
class TestShaoZiGuanMeiZhan(unittest.TestCase):
    """
    《梅花易數》原典觀梅占：
      辰年十二月十七日申時，觀梅見二雀爭枝墜地
      年5(辰) + 月12 + 日17 = 34 → 34%8=2 → 兌（上卦）
      +申時9 = 43 → 43%8=3 → 離（下卦）
      43%6=1 → 初爻動

    結果：
      本卦：澤火革（49）
      互卦：天風姤（44）
      變卦：澤山咸（31）
      體用：動爻在下 → 上兌為體（金），下離為用（火）→ 火剋金 = 用剋體（凶）
    """

    def test_classical_guanmeizhan(self):
        # lunar 2024 年地支為辰(5)
        result = qigua_by_time(year=2024, month=12, day=17, hour=15)

        # 本卦
        self.assertEqual(result["本卦"]["名稱"], "澤火革")
        self.assertEqual(result["本卦"]["序號"], 49)
        self.assertTrue(result["本卦"]["上卦"].startswith("兌"))
        self.assertTrue(result["本卦"]["下卦"].startswith("離"))
        self.assertEqual(result["本卦"]["二進位"], "011101")
        self.assertEqual(result["本卦"]["動爻"], "第1爻")

        # 互卦
        self.assertEqual(result["互卦"]["名稱"], "天風姤")
        self.assertEqual(result["互卦"]["上互"], "乾")
        self.assertEqual(result["互卦"]["下互"], "巽")

        # 變卦
        self.assertEqual(result["變卦"]["名稱"], "澤山咸")
        self.assertEqual(result["變卦"]["序號"], 31)

        # 體用：動初爻 → 上卦為體
        self.assertTrue(result["體用"]["體卦"].startswith("兌"))
        self.assertIn("上卦", result["體用"]["體卦"])
        self.assertIn("金", result["體用"]["體卦"])
        self.assertTrue(result["體用"]["用卦"].startswith("離"))
        self.assertIn("下卦", result["體用"]["用卦"])
        self.assertIn("火", result["體用"]["用卦"])
        self.assertIn("用克體", result["體用"]["生克關係"])

    def test_calculation_trace(self):
        result = qigua_by_time(year=2024, month=12, day=17, hour=15)
        trace = result["計算過程"]
        self.assertIn("辰", trace["年數"])
        self.assertIn("申", trace["時辰"])
        self.assertIn("34", trace["上卦數"])
        self.assertIn("43", trace["下卦數"])


# ============================================================================
# 4. 體用判定方向（動爻 ≤ 3 上卦為體；> 3 下卦為體）
# ============================================================================
class TestTiYongDirection(unittest.TestCase):

    def test_dong_in_lower_upper_is_ti(self):
        """動爻 1, 2, 3 → 動在下卦 → 上卦為體"""
        for dong in [1, 2, 3]:
            with self.subTest(dong=dong):
                result = qigua_by_numbers(1, 8, dong)  # 上乾 下坤
                self.assertTrue(result["體用"]["體卦"].startswith("乾"),
                                f"動爻 {dong} 在下，上卦乾應為體，實得 {result['體用']['體卦']}")

    def test_dong_in_upper_lower_is_ti(self):
        """動爻 4, 5, 6 → 動在上卦 → 下卦為體"""
        for dong in [4, 5, 6]:
            with self.subTest(dong=dong):
                result = qigua_by_numbers(1, 8, dong)  # 上乾 下坤
                self.assertTrue(result["體用"]["體卦"].startswith("坤"),
                                f"動爻 {dong} 在上，下卦坤應為體，實得 {result['體用']['體卦']}")


# ============================================================================
# 5. qigua_by_gregorian_time：西曆 → 農曆 → 起卦
# ============================================================================
class TestQiguaByGregorianTime(unittest.TestCase):
    """西曆入口應透過 gregorian_to_lunar 後與 qigua_by_time 結果一致"""

    def test_matches_lunar_qigua(self):
        """西曆 2024-02-10（即農曆 2024/1/1） + 巳時 11 點"""
        gz = qigua_by_gregorian_time(2024, 2, 10, 11)
        ln = qigua_by_time(2024, 1, 1, 11)
        # 本卦、變卦、互卦、動爻應完全一致
        self.assertEqual(gz["本卦"]["序號"], ln["本卦"]["序號"])
        self.assertEqual(gz["變卦"]["序號"], ln["變卦"]["序號"])
        self.assertEqual(gz["互卦"]["名稱"], ln["互卦"]["名稱"])
        self.assertEqual(gz["本卦"]["動爻"], ln["本卦"]["動爻"])

    def test_includes_date_conversion_info(self):
        gz = qigua_by_gregorian_time(2024, 2, 10, 11)
        self.assertIn("日期轉換", gz)
        self.assertIn("2024年2月10日", gz["日期轉換"]["西曆"])
        self.assertIn("2024", gz["日期轉換"]["農曆"])

    def test_leap_month_input(self):
        """西曆 2023-03-22 = 農曆 2023 閏二月初一，起卦應成功"""
        gz = qigua_by_gregorian_time(2023, 3, 22, 12)
        self.assertIn("日期轉換", gz)
        self.assertIn("閏", gz["日期轉換"]["農曆"])
        # 至少應產生合法卦序號
        self.assertIn(gz["本卦"]["序號"], range(1, 65))


# ============================================================================
# 6. 起卦結果結構完整性
# ============================================================================
class TestResultStructure(unittest.TestCase):
    """所有起卦函數都應返回相同的 dict 結構"""

    REQUIRED_KEYS = {"本卦", "體用", "互卦", "變卦"}

    def test_qigua_by_numbers_structure(self):
        result = qigua_by_numbers(3, 5)
        self.assertTrue(self.REQUIRED_KEYS.issubset(result.keys()))

    def test_qigua_by_time_structure(self):
        result = qigua_by_time(2024, 6, 15, 10)
        self.assertTrue(self.REQUIRED_KEYS.issubset(result.keys()))

    def test_qigua_by_gregorian_structure(self):
        result = qigua_by_gregorian_time(2024, 6, 15, 10)
        self.assertTrue(self.REQUIRED_KEYS.issubset(result.keys()))


# ============================================================================
# 7. 策略表變卦路徑（F1 回歸測試）
# ============================================================================
class TestStrategyChangePaths(unittest.TestCase):
    """每條 HEXAGRAM_STRATEGY change_path 的「變N爻」必須以自下而上的爻位
    （初爻=1 … 上爻=6，與 apply_change/print_result 一致）真正能將本卦變為
    所標示的目標卦。防止策略表的變爻位置被改回「自上而下」的鏡像錯誤。"""

    SHORT = {
        1: "乾", 2: "坤", 3: "屯", 4: "蒙", 5: "需", 6: "訟", 7: "師", 8: "比",
        9: "小畜", 10: "履", 11: "泰", 12: "否", 13: "同人", 14: "大有", 15: "謙",
        16: "豫", 17: "隨", 18: "蠱", 19: "臨", 20: "觀", 21: "噬嗑", 22: "賁",
        23: "剝", 24: "復", 25: "无妄", 26: "大畜", 27: "頤", 28: "大過", 29: "坎",
        30: "離", 31: "咸", 32: "恆", 33: "遯", 34: "大壯", 35: "晉", 36: "明夷",
        37: "家人", 38: "睽", 39: "蹇", 40: "解", 41: "損", 42: "益", 43: "夬",
        44: "姤", 45: "萃", 46: "升", 47: "困", 48: "井", 49: "革", 50: "鼎",
        51: "震", 52: "艮", 53: "漸", 54: "歸妹", 55: "豐", 56: "旅", 57: "巽",
        58: "兌", 59: "渙", 60: "節", 61: "中孚", 62: "小過", 63: "既濟", 64: "未濟",
    }

    def test_change_paths_use_bottom_up_yao(self):
        import re

        from meihua_calc import (
            HEXAGRAM_STRATEGY,
            HEXAGRAMS,
            apply_change,
            binary_to_gua_pair,
            get_hexagram_binary,
        )

        name_to_num = {v: k for k, v in self.SHORT.items()}
        num_to_bin = {num: get_hexagram_binary(u, l)
                      for (u, l), (num, _) in HEXAGRAMS.items()}

        checked = 0
        for num, (_, _, _, path) in HEXAGRAM_STRATEGY.items():
            if not path:
                continue
            m = re.search(r"變(\d)爻", path)
            if not m:
                continue  # 例：大過 → 夬 → 革（無單一變爻）
            yao = int(m.group(1))
            tgt_token = re.split(r"→", path)[-1]
            tgt_name = re.match(r"\s*([^（(]+)", tgt_token).group(1).strip()
            self.assertIn(tgt_name, name_to_num,
                          f"卦{num}：無法解析目標卦名 {tgt_name!r} ← {path!r}")
            changed = apply_change(num_to_bin[num], yao)
            got = HEXAGRAMS[binary_to_gua_pair(changed)][0]
            self.assertEqual(
                got, name_to_num[tgt_name],
                f"卦{num} {self.SHORT[num]}：變{yao}爻得 {self.SHORT.get(got)}({got})，"
                f"但路徑宣稱變為 {tgt_name}({name_to_num[tgt_name]})：{path!r}")
            checked += 1
        self.assertGreaterEqual(checked, 38,
                                f"可解析的變卦路徑應 ≥38 條，實得 {checked}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
