#!/usr/bin/env python3
"""
Tier 2：八宮歸宮 + 世應位置單元測試

驗證項目：
  1. PALACE_ORDER 涵蓋 64 卦且無重複（基本完整性）
  2. 京房八宮『遞變陰陽』結構規則對 8 宮成立
     - 本宮 / 一世 / 二世 / 三世 / 四世 / 五世 / 游魂 / 歸魂
  3. SHI_POS / YING_POS 與世代對應規律一致
  4. 世應永遠隔三位
  5. HEX_TO_PALACE 反查表自洽
  6. 八宮五行對應正確（乾兌金、離火、震巽木、坎水、艮坤土）
  7. 抽樣已知卦的歸宮 + 世應對照

若 PALACE_ORDER 任一卦錯位 → 該卦六親、用神、世應全錯。
京房八宮結構測試 = 同時驗 PALACE_ORDER + apply_change + 京房規則。
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from meihua_calc import BAGUA, HEXAGRAMS, apply_change, binary_to_gua_pair  # noqa: E402
from najia import (  # noqa: E402
    GENERATION_NAME,
    HEX_TO_PALACE,
    PALACE_NAME,
    PALACE_ORDER,
    PALACE_WUXING,
    SHI_POS,
    YING_POS,
    annotate,
)


# 京房八宮『遞變陰陽』規則：從本宮卦逐步翻爻得各世代
# - 本宮 → 五世：從初爻起逐爻翻轉
# - 游魂：從五世卦再翻回第 4 爻（等於從本宮翻 1+2+3+5）
# - 歸魂：從游魂卦再把內卦三爻翻回本宮（等於從本宮只翻第 5 爻）
GEN_FLIPS = {
    0: [],              # 本宮
    1: [1],             # 一世
    2: [1, 2],          # 二世
    3: [1, 2, 3],       # 三世
    4: [1, 2, 3, 4],    # 四世
    5: [1, 2, 3, 4, 5], # 五世
    6: [1, 2, 3, 5],    # 游魂
    7: [5],             # 歸魂
}


def _hex_binary(hex_num: int) -> str:
    """由卦號回查 binary"""
    for (u, l), (num, _) in HEXAGRAMS.items():
        if num == hex_num:
            return BAGUA[u]["binary"] + BAGUA[l]["binary"]
    raise KeyError(f"找不到卦號 {hex_num}")


# ============================================================================
# 1. PALACE_ORDER 完整性
# ============================================================================
class TestPalaceCoverage(unittest.TestCase):

    def test_eight_palaces(self):
        self.assertEqual(set(PALACE_ORDER.keys()), set(range(1, 9)))

    def test_each_palace_has_eight_hexagrams(self):
        for palace, seq in PALACE_ORDER.items():
            self.assertEqual(len(seq), 8, f"宮 {palace} 應有 8 卦，實得 {len(seq)}")

    def test_covers_all_64_hexagrams_exactly_once(self):
        all_hex = [h for seq in PALACE_ORDER.values() for h in seq]
        self.assertEqual(sorted(all_hex), list(range(1, 65)),
                         "PALACE_ORDER 應涵蓋 1-64 全部卦號且無重複")

    def test_hex_to_palace_reverse_lookup(self):
        """HEX_TO_PALACE 應與 PALACE_ORDER 一致"""
        for palace, seq in PALACE_ORDER.items():
            for gen, hex_num in enumerate(seq):
                self.assertEqual(HEX_TO_PALACE[hex_num], (palace, gen))
        self.assertEqual(len(HEX_TO_PALACE), 64)


# ============================================================================
# 2. 京房八宮結構規則（最強的測試）
# ============================================================================
class TestPalaceStructuralRule(unittest.TestCase):
    """
    用京房八宮『遞變陰陽』規則重新推算 8 宮 × 8 卦 = 64 卦，
    必須與 PALACE_ORDER 表完全一致。

    這個測試同時驗：
      - PALACE_ORDER 表本身
      - apply_change 的爻位映射
      - 京房八宮的歷史規則
    任一錯 → 64 個斷言中至少一個會 fail。
    """

    def test_all_palaces_follow_jing_fang_rule(self):
        for palace, hex_seq in PALACE_ORDER.items():
            ben_hex_num = hex_seq[0]
            ben_bin = _hex_binary(ben_hex_num)

            for gen, hex_num in enumerate(hex_seq):
                expected_bin = ben_bin
                for p in GEN_FLIPS[gen]:
                    expected_bin = apply_change(expected_bin, p)
                u, l = binary_to_gua_pair(expected_bin)
                actual_num, actual_name = HEXAGRAMS[(u, l)]
                self.assertEqual(
                    actual_num, hex_num,
                    f"{PALACE_NAME[palace]}宮{GENERATION_NAME[gen]} "
                    f"表中為卦 {hex_num}，京房規則推導得 {actual_num}({actual_name})"
                )

    def test_ben_gua_is_pure_double_trigram(self):
        """每宮本宮卦必為純卦（上下卦同）"""
        for palace, seq in PALACE_ORDER.items():
            ben_hex = seq[0]
            ben_bin = _hex_binary(ben_hex)
            self.assertEqual(ben_bin[:3], ben_bin[3:],
                             f"{PALACE_NAME[palace]}宮本宮卦 {ben_hex} 應為純卦")


# ============================================================================
# 3. 世應位置
# ============================================================================
class TestShiYingPosition(unittest.TestCase):
    """世應位置必須符合『八宮卦次』固定規律"""

    EXPECTED_SHI = {0: 6, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 4, 7: 3}
    EXPECTED_YING = {0: 3, 1: 4, 2: 5, 3: 6, 4: 1, 5: 2, 6: 1, 7: 6}

    def test_shi_pos_values(self):
        for gen, expected_shi in self.EXPECTED_SHI.items():
            self.assertEqual(SHI_POS[gen], expected_shi,
                             f"{GENERATION_NAME[gen]} 世位應為 {expected_shi}")

    def test_ying_pos_values(self):
        for gen, expected_ying in self.EXPECTED_YING.items():
            self.assertEqual(YING_POS[gen], expected_ying,
                             f"{GENERATION_NAME[gen]} 應位應為 {expected_ying}")

    def test_shi_ying_distance_always_three(self):
        """世應之距永遠為 3 爻（含游魂、歸魂例外宮在內）"""
        for gen in range(8):
            distance = abs(SHI_POS[gen] - YING_POS[gen])
            self.assertEqual(distance, 3,
                             f"{GENERATION_NAME[gen]} 世({SHI_POS[gen]})應({YING_POS[gen]}) 距離應為 3")

    def test_shi_ying_in_valid_range(self):
        for gen in range(8):
            self.assertIn(SHI_POS[gen], range(1, 7))
            self.assertIn(YING_POS[gen], range(1, 7))


# ============================================================================
# 4. 八宮五行
# ============================================================================
class TestPalaceWuxing(unittest.TestCase):
    EXPECTED = {
        1: "金", 2: "金",  # 乾、兌
        3: "火",            # 離
        4: "木", 5: "木",  # 震、巽
        6: "水",            # 坎
        7: "土", 8: "土",  # 艮、坤
    }

    def test_palace_wuxing(self):
        for palace, expected in self.EXPECTED.items():
            self.assertEqual(PALACE_WUXING[palace], expected,
                             f"{PALACE_NAME[palace]}宮五行應為 {expected}")


# ============================================================================
# 5. 抽樣已知歸宮 + 世應對照（黃金測試樣本）
# ============================================================================
class TestKnownHexagramAttribution(unittest.TestCase):
    """
    對照《卜筮正宗》《增刪卜易》八宮卦次表的抽樣驗證。
    若 PALACE_ORDER 哪卦錯位，這裡會立刻被抓到。

    格式：(卦號, 卦名, 期望宮, 期望世代, 期望世位, 期望應位)
    """

    SAMPLES = [
        # 乾宮 8 卦
        (1,  "乾為天",  1, 0, 6, 3),  # 本宮
        (44, "天風姤",  1, 1, 1, 4),  # 一世
        (33, "天山遯",  1, 2, 2, 5),  # 二世
        (12, "天地否",  1, 3, 3, 6),  # 三世
        (20, "風地觀",  1, 4, 4, 1),  # 四世
        (23, "山地剝",  1, 5, 5, 2),  # 五世
        (35, "火地晉",  1, 6, 4, 1),  # 游魂
        (14, "火天大有", 1, 7, 3, 6),  # 歸魂
        # 各宮抽樣
        (57, "巽為風",  5, 0, 6, 3),  # 巽宮本宮
        (3,  "水雷屯",  6, 2, 2, 5),  # 坎宮二世
        (38, "火澤睽",  7, 4, 4, 1),  # 艮宮四世
        (36, "地火明夷", 6, 6, 4, 1),  # 坎宮游魂
        (2,  "坤為地",  8, 0, 6, 3),  # 坤宮本宮
        (8,  "水地比",  8, 7, 3, 6),  # 坤宮歸魂
        (51, "震為雷",  4, 0, 6, 3),  # 震宮本宮
        (52, "艮為山",  7, 0, 6, 3),  # 艮宮本宮
        (29, "坎為水",  6, 0, 6, 3),  # 坎宮本宮
        (30, "離為火",  3, 0, 6, 3),  # 離宮本宮
        (58, "兌為澤",  2, 0, 6, 3),  # 兌宮本宮
    ]

    def test_sample_attributions(self):
        for hex_num, name, exp_palace, exp_gen, exp_shi, exp_ying in self.SAMPLES:
            with self.subTest(卦=name):
                palace, gen = HEX_TO_PALACE[hex_num]
                self.assertEqual(palace, exp_palace,
                                 f"{name} 應屬{PALACE_NAME[exp_palace]}宮")
                self.assertEqual(gen, exp_gen,
                                 f"{name} 應為{GENERATION_NAME[exp_gen]}")
                self.assertEqual(SHI_POS[gen], exp_shi,
                                 f"{name} 世位應為第{exp_shi}爻")
                self.assertEqual(YING_POS[gen], exp_ying,
                                 f"{name} 應位應為第{exp_ying}爻")


# ============================================================================
# 6. annotate() end-to-end：確保 najia.annotate 用對表
# ============================================================================
class TestAnnotateIntegration(unittest.TestCase):
    """以 annotate() 跑幾個 binary，驗證最終裝卦結果"""

    def test_xun_wei_feng(self):
        """巽為風 = 110110"""
        h = annotate("110110")
        self.assertEqual(h.hex_name, "巽為風")
        self.assertEqual(h.palace_name, "巽")
        self.assertEqual(h.generation_name, "本宮")
        self.assertEqual(h.palace_wuxing, "木")
        self.assertEqual(h.shi_pos, 6)
        self.assertEqual(h.ying_pos, 3)
        self.assertTrue(h.yaos[5].is_shi)   # 第6爻
        self.assertTrue(h.yaos[2].is_ying)  # 第3爻

    def test_huo_di_jin_youhun(self):
        """火地晉 = 101000，乾宮游魂"""
        h = annotate("101000")
        self.assertEqual(h.hex_name, "火地晉")
        self.assertEqual(h.palace_name, "乾")
        self.assertEqual(h.generation_name, "游魂")
        self.assertEqual(h.shi_pos, 4)
        self.assertEqual(h.ying_pos, 1)

    def test_huo_tian_dayou_guihun(self):
        """火天大有 = 101111，乾宮歸魂"""
        h = annotate("101111")
        self.assertEqual(h.hex_name, "火天大有")
        self.assertEqual(h.palace_name, "乾")
        self.assertEqual(h.generation_name, "歸魂")
        self.assertEqual(h.shi_pos, 3)
        self.assertEqual(h.ying_pos, 6)

    def test_di_huo_mingyi_youhun(self):
        """地火明夷 = 000101，坎宮游魂"""
        h = annotate("000101")
        self.assertEqual(h.hex_name, "地火明夷")
        self.assertEqual(h.palace_name, "坎")
        self.assertEqual(h.generation_name, "游魂")
        self.assertEqual(h.palace_wuxing, "水")


if __name__ == "__main__":
    unittest.main(verbosity=2)
