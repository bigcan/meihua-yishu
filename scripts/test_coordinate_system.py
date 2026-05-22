#!/usr/bin/env python3
"""
Tier 1：基礎座標系單元測試

驗證項目（按風險排序）：
  1. binary 編碼方向慣例（meihua_calc.BAGUA / HEXAGRAMS / binary_to_gua_pair 三方一致）
  2. CoinHexagram.ben_binary() 與 meihua_calc 慣例對齊
  3. apply_change / CoinHexagram.bian_binary() 的爻位 → index 映射
  4. get_hu_gua 取爻方向與順序
  5. 純陽 / 純陰互卦邊界處理
  6. 0 動 / 6 動 / 多動爻

任一測試失敗 → 整個系統的「卦名」「動爻」「變卦」可能都偏掉。
執行：
  python scripts/test_coordinate_system.py
  或：pytest scripts/test_coordinate_system.py -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from meihua_calc import (  # noqa: E402
    BAGUA,
    BINARY_TO_GUA,
    HEXAGRAMS,
    apply_change,
    binary_to_gua_pair,
    get_hexagram_binary,
    get_hu_gua,
)
from jinqian_gua import CoinHexagram, analyze, manual_hexagram  # noqa: E402


# ----------------------------------------------------------------------------
# 共用：擲卦符號（從下而上 6 次）
# ----------------------------------------------------------------------------
YANG_STATIC = "背字字"   # 少陽 sum=7
YIN_STATIC = "背背字"    # 少陰 sum=8
YANG_DONG = "背背背"     # 老陽 sum=9（陽變陰）
YIN_DONG = "字字字"      # 老陰 sum=6（陰變陽）


# ============================================================================
# 1. binary 表內部一致性（不依賴 jinqian_gua）
# ============================================================================
class TestBinaryConvention(unittest.TestCase):
    """純粹驗 meihua_calc 內部表的方向慣例"""

    def test_bagua_binary_lengths(self):
        for n, info in BAGUA.items():
            self.assertEqual(len(info["binary"]), 3, f"卦 {n} binary 長度應為 3")

    def test_binary_to_gua_roundtrip(self):
        """BAGUA → BINARY_TO_GUA 雙向應一致"""
        for n, info in BAGUA.items():
            self.assertEqual(BINARY_TO_GUA[info["binary"]], n)

    def test_hexagram_binary_concat_order(self):
        """get_hexagram_binary(u, l) 必須是 upper + lower（前 3 位 = 上卦）"""
        # 天澤履：上乾(111) 下兌(011) → 111011
        self.assertEqual(get_hexagram_binary(1, 2), "111011")
        # 澤天夬：上兌(011) 下乾(111) → 011111
        self.assertEqual(get_hexagram_binary(2, 1), "011111")

    def test_binary_to_gua_pair_splits_correctly(self):
        """binary_to_gua_pair 應把前 3 位視為上卦、後 3 位視為下卦"""
        u, l = binary_to_gua_pair("111011")
        self.assertEqual((u, l), (1, 2), "111011 應解析為 上乾 下兌")
        u, l = binary_to_gua_pair("011111")
        self.assertEqual((u, l), (2, 1), "011111 應解析為 上兌 下乾")

    def test_hexagrams_64_complete(self):
        """64 卦表必須完整且無重號"""
        self.assertEqual(len(HEXAGRAMS), 64)
        nums = [v[0] for v in HEXAGRAMS.values()]
        self.assertEqual(sorted(nums), list(range(1, 65)))

    def test_all_hexagrams_roundtrip(self):
        """所有 64 卦：get_hexagram_binary → binary_to_gua_pair 應還原"""
        for (u, l) in HEXAGRAMS:
            binary = get_hexagram_binary(u, l)
            u2, l2 = binary_to_gua_pair(binary)
            self.assertEqual((u, l), (u2, l2), f"卦 ({u},{l}) 雙向轉換不一致")


# ============================================================================
# 2. apply_change：動爻 index 映射
# ============================================================================
class TestApplyChange(unittest.TestCase):
    """動爻位置 → binary index 的映射（容易把方向搞反的地方）"""

    def test_position_to_index(self):
        """pos 1 (初爻) → binary 最右字元；pos 6 (上爻) → 最左字元"""
        # 從乾(111111) 改 pos 1 → 第 6 位由 1 變 0 → "111110"
        self.assertEqual(apply_change("111111", 1), "111110")
        # 改 pos 6 → 第 1 位由 1 變 0 → "011111"
        self.assertEqual(apply_change("111111", 6), "011111")
        # 改 pos 3 → index 3（中間偏右）→ "111011"
        self.assertEqual(apply_change("111111", 3), "111011")

    def test_reversibility(self):
        """連改兩次同一爻應還原"""
        for pos in range(1, 7):
            original = "101010"
            once = apply_change(original, pos)
            twice = apply_change(once, pos)
            self.assertEqual(twice, original, f"pos {pos} 連改兩次未還原")

    def test_classical_qian_chu_yao_dong(self):
        """乾卦初爻動 → 天風姤（卦 44）"""
        bian = apply_change("111111", 1)
        u, l = binary_to_gua_pair(bian)
        num, name = HEXAGRAMS[(u, l)]
        self.assertEqual((num, name), (44, "天風姤"))

    def test_classical_kun_shang_yao_dong(self):
        """坤卦上爻動 → 山地剝（卦 23）"""
        bian = apply_change("000000", 6)
        u, l = binary_to_gua_pair(bian)
        num, name = HEXAGRAMS[(u, l)]
        self.assertEqual((num, name), (23, "山地剝"))


# ============================================================================
# 3. get_hu_gua：互卦取爻方向
# ============================================================================
class TestHuGua(unittest.TestCase):
    """互卦規則：下互 = 2,3,4 爻；上互 = 3,4,5 爻"""

    def test_classical_zhun_hu_is_bo(self):
        """水雷屯（010001）互卦應為山地剝（卦 23）"""
        # 屯：pos1=陽 pos2=陰 pos3=陰 pos4=陰 pos5=陽 pos6=陰
        hu_u, hu_l = get_hu_gua("010001")
        num, name = HEXAGRAMS[(hu_u, hu_l)]
        self.assertEqual((num, name), (23, "山地剝"),
                         f"水雷屯互卦應為山地剝，實得 ({hu_u},{hu_l})={name}")

    def test_classical_jiji_hu_is_weiji(self):
        """水火既濟（010101）互卦應為火水未濟（卦 64）"""
        hu_u, hu_l = get_hu_gua("010101")
        num, name = HEXAGRAMS[(hu_u, hu_l)]
        self.assertEqual((num, name), (64, "火水未濟"))

    def test_qian_hu_is_qian(self):
        """純陽乾互卦仍為乾"""
        hu_u, hu_l = get_hu_gua("111111")
        self.assertEqual((hu_u, hu_l), (1, 1))

    def test_kun_hu_is_kun(self):
        """純陰坤互卦仍為坤"""
        hu_u, hu_l = get_hu_gua("000000")
        self.assertEqual((hu_u, hu_l), (8, 8))


# ============================================================================
# 4. CoinHexagram：銅錢結果 → binary 慣例對齊
# ============================================================================
class TestCoinHexagramBinary(unittest.TestCase):
    """擲卦結果（自下而上）必須生成與 meihua_calc 一致的 binary"""

    def test_tianzeli_static(self):
        """天澤履（卦 10）：上乾下兌，全靜
           pos 1-2-3-4-5-6 = 陽 陽 陰 陽 陽 陽
        """
        h = manual_hexagram([
            YANG_STATIC, YANG_STATIC, YIN_STATIC,
            YANG_STATIC, YANG_STATIC, YANG_STATIC,
        ])
        self.assertEqual(h.ben_binary(), "111011")
        u, l = binary_to_gua_pair(h.ben_binary())
        self.assertEqual(HEXAGRAMS[(u, l)], (10, "天澤履"))
        self.assertEqual(h.changing_positions(), [])
        # 無動爻 → 變卦同本卦
        self.assertEqual(h.bian_binary(), h.ben_binary())

    def test_zetianguai_static(self):
        """澤天夬（卦 43）：上兌下乾（驗證上下卦不互換）
           pos 1-2-3-4-5 = 陽，pos 6 = 陰
        """
        h = manual_hexagram([
            YANG_STATIC, YANG_STATIC, YANG_STATIC,
            YANG_STATIC, YANG_STATIC, YIN_STATIC,
        ])
        self.assertEqual(h.ben_binary(), "011111")
        u, l = binary_to_gua_pair(h.ben_binary())
        self.assertEqual(HEXAGRAMS[(u, l)], (43, "澤天夬"))

    def test_qian_chu_yao_dong(self):
        """乾卦初爻動 → 變天風姤"""
        h = manual_hexagram([
            YANG_DONG, YANG_STATIC, YANG_STATIC,
            YANG_STATIC, YANG_STATIC, YANG_STATIC,
        ])
        self.assertEqual(h.ben_binary(), "111111")
        self.assertEqual(h.bian_binary(), "111110")
        self.assertEqual(h.changing_positions(), [1])
        u, l = binary_to_gua_pair(h.bian_binary())
        self.assertEqual(HEXAGRAMS[(u, l)], (44, "天風姤"))

    def test_kun_shang_yao_dong(self):
        """坤卦上爻動 → 變山地剝"""
        h = manual_hexagram([
            YIN_STATIC, YIN_STATIC, YIN_STATIC,
            YIN_STATIC, YIN_STATIC, YIN_DONG,
        ])
        self.assertEqual(h.ben_binary(), "000000")
        self.assertEqual(h.bian_binary(), "100000")
        self.assertEqual(h.changing_positions(), [6])
        u, l = binary_to_gua_pair(h.bian_binary())
        self.assertEqual(HEXAGRAMS[(u, l)], (23, "山地剝"))

    def test_multi_dong_yao(self):
        """乾卦初+上爻同動 → 變澤風大過（卦 28）"""
        h = manual_hexagram([
            YANG_DONG, YANG_STATIC, YANG_STATIC,
            YANG_STATIC, YANG_STATIC, YANG_DONG,
        ])
        self.assertEqual(h.ben_binary(), "111111")
        self.assertEqual(h.bian_binary(), "011110")
        self.assertEqual(sorted(h.changing_positions()), [1, 6])
        u, l = binary_to_gua_pair(h.bian_binary())
        self.assertEqual(HEXAGRAMS[(u, l)], (28, "澤風大過"))


# ============================================================================
# 5. 邊界案例：純陽 / 純陰 互卦
# ============================================================================
class TestPureYinYangHu(unittest.TestCase):
    """analyze() 對純乾純坤互卦的特殊處理"""

    def test_pure_qian_no_dong_hu_equals_qian(self):
        h = manual_hexagram([YANG_STATIC] * 6)
        result = analyze(h)
        self.assertEqual(result["互卦"]["名稱"], "乾為天")
        self.assertIn("純陽/純陰且無動爻", result["互卦"]["註"])

    def test_pure_qian_with_dong_hu_from_bian(self):
        """乾卦有動爻時，互卦應取自變卦"""
        h = manual_hexagram([
            YANG_STATIC, YANG_STATIC, YANG_DONG,   # 第3爻動
            YANG_STATIC, YANG_STATIC, YANG_STATIC,
        ])
        result = analyze(h)
        # bian = 111011 = 履，履的互卦 = [1:4]=110 巽, [2:5]=101 離 → 風火家人
        self.assertEqual(result["互卦"]["名稱"], "風火家人")
        self.assertIn("互卦取自變卦", result["互卦"]["註"])

    def test_pure_kun_no_dong_hu_equals_kun(self):
        h = manual_hexagram([YIN_STATIC] * 6)
        result = analyze(h)
        self.assertEqual(result["互卦"]["名稱"], "坤為地")


# ============================================================================
# 6. 動爻數量 → 朱熹解卦法主爻判定
# ============================================================================
class TestZhuxiMainYao(unittest.TestCase):
    """驗證 0/1/2/4/5/6 動爻時主爻判定方向不會反"""

    def test_zero_dong(self):
        h = manual_hexagram([YANG_STATIC] * 6)
        result = analyze(h)
        self.assertEqual(result["動爻"]["數量"], 0)
        self.assertIsNone(result["動爻"]["主爻"])

    def test_two_dong_takes_upper(self):
        """2 動：以上爻為主"""
        h = manual_hexagram([
            YANG_DONG, YANG_STATIC, YANG_STATIC,
            YANG_STATIC, YANG_DONG, YANG_STATIC,
        ])
        result = analyze(h)
        self.assertEqual(result["動爻"]["位置"], [1, 5])
        self.assertIn("第5爻", result["動爻"]["主爻"])  # 不應是第1爻

    def test_four_dong_takes_lower_static(self):
        """4 動：看變卦兩不動爻，以下爻為主"""
        h = manual_hexagram([
            YANG_DONG, YANG_STATIC, YANG_DONG,
            YANG_STATIC, YANG_DONG, YANG_DONG,
        ])
        result = analyze(h)
        # 不動爻 = pos 2, 4
        self.assertEqual(sorted(result["動爻"]["位置"]), [1, 3, 5, 6])
        self.assertIn("第2爻", result["動爻"]["主爻"])  # 不應是第4爻

    def test_six_dong_qian_yongjiu(self):
        """乾卦六爻全動 → 用九"""
        h = manual_hexagram([YANG_DONG] * 6)
        result = analyze(h)
        self.assertEqual(result["動爻"]["數量"], 6)
        self.assertIn("用九", result["動爻"]["主爻"])

    def test_six_dong_kun_yongliu(self):
        """坤卦六爻全動 → 用六"""
        h = manual_hexagram([YIN_DONG] * 6)
        result = analyze(h)
        self.assertEqual(result["動爻"]["數量"], 6)
        self.assertIn("用六", result["動爻"]["主爻"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
