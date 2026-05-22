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


if __name__ == "__main__":
    unittest.main(verbosity=2)
