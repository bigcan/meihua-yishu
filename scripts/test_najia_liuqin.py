#!/usr/bin/env python3
"""
Tier 3：納甲查表 + 六親判定單元測試

驗證項目：
  1. PURE_GUA_NAJIA 八純卦六爻干支配置
     - 天干配宮：乾甲壬、坤乙癸、震庚、巽辛、坎戊、離己、艮丙、兌丁
     - 內外卦交界：乾內甲外壬、坤內乙外癸
     - 地支陽順陰逆：乾子寅辰／午申戌（順）、坤未巳卯／丑亥酉（逆）等
  2. hex_najia 內外卦合成：下三爻取下卦純卦下三爻、上三爻取上卦純卦上三爻
  3. liuqin_from 五行 → 六親：25 組（5 五行 × 5 五行）完整對照
  4. 黃金卦例：5 個已知卦從《增刪卜易》《卜筮正宗》原書六親逐爻對照
     - 乾為天、坤為地、巽為風、水雷屯、火澤睽

任一錯 → 該卦六親、用神、世應全錯，導致斷卦結論偏離。
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from najia import (  # noqa: E402
    PURE_GUA_NAJIA,
    ZHI_WUXING,
    annotate,
    hex_najia,
    liuqin_from,
)


# ============================================================================
# 1. 八純卦納甲表（按《增刪卜易》卷一納甲歌訣）
# ============================================================================
class TestPureGuaNajia(unittest.TestCase):
    """逐宮逐爻核對純卦干支配置"""

    # 八宮純卦六爻干支（初爻到上爻）
    # 對照《增刪卜易》卷一「八宮所屬」與「納甲歌訣」
    EXPECTED = {
        1: ["甲子", "甲寅", "甲辰", "壬午", "壬申", "壬戌"],  # 乾：內甲外壬，陽支順子寅辰／午申戌
        2: ["丁巳", "丁卯", "丁丑", "丁亥", "丁酉", "丁未"],  # 兌：丁，陰支逆從巳起
        3: ["己卯", "己丑", "己亥", "己酉", "己未", "己巳"],  # 離：己，陰支逆從卯起
        4: ["庚子", "庚寅", "庚辰", "庚午", "庚申", "庚戌"],  # 震：庚，陽支順從子起
        5: ["辛丑", "辛亥", "辛酉", "辛未", "辛巳", "辛卯"],  # 巽：辛，陰支逆從丑起
        6: ["戊寅", "戊辰", "戊午", "戊申", "戊戌", "戊子"],  # 坎：戊，陽支順從寅起
        7: ["丙辰", "丙午", "丙申", "丙戌", "丙子", "丙寅"],  # 艮：丙，陽支順從辰起
        8: ["乙未", "乙巳", "乙卯", "癸丑", "癸亥", "癸酉"],  # 坤：內乙外癸，陰支逆未巳卯／丑亥酉
    }

    def test_all_eight_palaces(self):
        for palace, expected in self.EXPECTED.items():
            self.assertEqual(PURE_GUA_NAJIA[palace], expected,
                             f"宮 {palace} 純卦納甲不符")

    def test_qian_internal_external_gan(self):
        """乾內三爻納甲、外三爻納壬"""
        for i in range(3):
            self.assertTrue(PURE_GUA_NAJIA[1][i].startswith("甲"))
        for i in range(3, 6):
            self.assertTrue(PURE_GUA_NAJIA[1][i].startswith("壬"))

    def test_kun_internal_external_gan(self):
        """坤內三爻納乙、外三爻納癸"""
        for i in range(3):
            self.assertTrue(PURE_GUA_NAJIA[8][i].startswith("乙"))
        for i in range(3, 6):
            self.assertTrue(PURE_GUA_NAJIA[8][i].startswith("癸"))

    def test_single_gan_palaces(self):
        """震庚、巽辛、坎戊、離己、艮丙、兌丁：六爻同一天干"""
        single = {4: "庚", 5: "辛", 6: "戊", 3: "己", 7: "丙", 2: "丁"}
        for palace, gan in single.items():
            for i in range(6):
                self.assertTrue(
                    PURE_GUA_NAJIA[palace][i].startswith(gan),
                    f"宮 {palace} 第 {i+1} 爻天干應為 {gan}"
                )

    def test_zhi_yang_palaces_progress(self):
        """陽支宮（乾震坎艮）地支應為陽支（子寅辰午申戌）"""
        yang_zhi = {"子", "寅", "辰", "午", "申", "戌"}
        for palace in [1, 4, 6, 7]:
            for gz in PURE_GUA_NAJIA[palace]:
                self.assertIn(gz[1], yang_zhi,
                              f"宮 {palace} 應全用陽支，違例：{gz}")

    def test_zhi_yin_palaces_regress(self):
        """陰支宮（坤兌離巽）地支應為陰支（丑卯巳未酉亥）"""
        yin_zhi = {"丑", "卯", "巳", "未", "酉", "亥"}
        for palace in [8, 2, 3, 5]:
            for gz in PURE_GUA_NAJIA[palace]:
                self.assertIn(gz[1], yin_zhi,
                              f"宮 {palace} 應全用陰支，違例：{gz}")


# ============================================================================
# 2. hex_najia 內外卦合成
# ============================================================================
class TestHexNajiaConstruction(unittest.TestCase):
    """下三爻取下卦純卦下三爻、上三爻取上卦純卦上三爻"""

    def test_qian_self(self):
        """乾為天 = 全乾"""
        self.assertEqual(hex_najia(1, 1), PURE_GUA_NAJIA[1])

    def test_kun_self(self):
        self.assertEqual(hex_najia(8, 8), PURE_GUA_NAJIA[8])

    def test_zhun_water_thunder(self):
        """水雷屯：上坎(6) 下震(4)
           下三爻 = 震[:3] = 庚子庚寅庚辰
           上三爻 = 坎[3:] = 戊申戊戌戊子
        """
        expected = ["庚子", "庚寅", "庚辰", "戊申", "戊戌", "戊子"]
        self.assertEqual(hex_najia(6, 4), expected)

    def test_kui_fire_lake(self):
        """火澤睽：上離(3) 下兌(2)
           下三爻 = 兌[:3] = 丁巳丁卯丁丑
           上三爻 = 離[3:] = 己酉己未己巳
        """
        expected = ["丁巳", "丁卯", "丁丑", "己酉", "己未", "己巳"]
        self.assertEqual(hex_najia(3, 2), expected)

    def test_tai_earth_heaven(self):
        """地天泰：上坤(8) 下乾(1)
           下三爻 = 乾[:3] = 甲子甲寅甲辰
           上三爻 = 坤[3:] = 癸丑癸亥癸酉
        """
        expected = ["甲子", "甲寅", "甲辰", "癸丑", "癸亥", "癸酉"]
        self.assertEqual(hex_najia(8, 1), expected)


# ============================================================================
# 3. liuqin_from 五行 → 六親（25 組完整對照）
# ============================================================================
class TestLiuqinFrom(unittest.TestCase):
    """
    以宮卦五行為「我」：
      - 同我=兄弟  生我=父母  我生=子孫  剋我=官鬼  我剋=妻財
    """

    # palace_wuxing → yao_wuxing → liuqin
    EXPECTED_TABLE = {
        "金": {"金": "兄弟", "水": "子孫", "土": "父母", "木": "妻財", "火": "官鬼"},
        "木": {"木": "兄弟", "火": "子孫", "水": "父母", "土": "妻財", "金": "官鬼"},
        "水": {"水": "兄弟", "木": "子孫", "金": "父母", "火": "妻財", "土": "官鬼"},
        "火": {"火": "兄弟", "土": "子孫", "木": "父母", "金": "妻財", "水": "官鬼"},
        "土": {"土": "兄弟", "金": "子孫", "火": "父母", "水": "妻財", "木": "官鬼"},
    }

    def test_all_25_combinations(self):
        for palace_wx, yao_map in self.EXPECTED_TABLE.items():
            for yao_wx, expected_liuqin in yao_map.items():
                with self.subTest(宮=palace_wx, 爻=yao_wx):
                    actual = liuqin_from(palace_wx, yao_wx)
                    self.assertEqual(
                        actual, expected_liuqin,
                        f"宮{palace_wx}遇爻{yao_wx}應為「{expected_liuqin}」，"
                        f"實得「{actual}」"
                    )

    def test_no_unknown_results(self):
        """5×5 = 25 組都應有明確六親，不得返回 '?'"""
        wuxings = ["金", "木", "水", "火", "土"]
        for p in wuxings:
            for y in wuxings:
                self.assertNotEqual(liuqin_from(p, y), "?",
                                    f"({p}, {y}) 不應為未知")


# ============================================================================
# 4. 黃金卦例：對照《增刪卜易》原書六親
# ============================================================================
class TestGoldenHexagramLiuqin(unittest.TestCase):
    """
    從《增刪卜易》《卜筮正宗》原書收錄的六親排列逐爻對照。
    格式：(binary, 卦名, 期望六親 [初爻到上爻])
    """

    GOLDEN_CASES = [
        # 乾為天（乾宮金）
        # 子孫(初甲子水) 妻財(甲寅木) 父母(甲辰土) 官鬼(壬午火) 兄弟(壬申金) 父母(壬戌土)
        ("111111", "乾為天",
         ["子孫", "妻財", "父母", "官鬼", "兄弟", "父母"]),

        # 坤為地（坤宮土）
        # 兄弟(乙未土) 父母(乙巳火) 官鬼(乙卯木) 兄弟(癸丑土) 妻財(癸亥水) 子孫(癸酉金)
        ("000000", "坤為地",
         ["兄弟", "父母", "官鬼", "兄弟", "妻財", "子孫"]),

        # 巽為風（巽宮木）—— 與 random 跑出來的結果一致
        # 妻財(辛丑土) 父母(辛亥水) 官鬼(辛酉金) 妻財(辛未土) 子孫(辛巳火) 兄弟(辛卯木)
        ("110110", "巽為風",
         ["妻財", "父母", "官鬼", "妻財", "子孫", "兄弟"]),

        # 水雷屯（坎宮水）
        # 兄弟(庚子水) 子孫(庚寅木) 官鬼(庚辰土) 父母(戊申金) 官鬼(戊戌土) 兄弟(戊子水)
        ("010001", "水雷屯",
         ["兄弟", "子孫", "官鬼", "父母", "官鬼", "兄弟"]),

        # 火澤睽（艮宮土）
        # 父母(丁巳火) 官鬼(丁卯木) 兄弟(丁丑土) 子孫(己酉金) 兄弟(己未土) 父母(己巳火)
        ("101011", "火澤睽",
         ["父母", "官鬼", "兄弟", "子孫", "兄弟", "父母"]),
    ]

    def test_all_golden_cases(self):
        for binary, name, expected_liuqin in self.GOLDEN_CASES:
            with self.subTest(卦=name):
                h = annotate(binary)
                self.assertEqual(h.hex_name, name,
                                 f"binary {binary} 應為 {name}")
                actual_liuqin = [y.liuqin for y in h.yaos]
                self.assertEqual(
                    actual_liuqin, expected_liuqin,
                    f"{name} 六親應為 {expected_liuqin}，實得 {actual_liuqin}"
                )

    def test_qian_najia_zhi_wuxing(self):
        """乾為天每爻地支五行驗證"""
        h = annotate("111111")
        expected = [("子", "水"), ("寅", "木"), ("辰", "土"),
                    ("午", "火"), ("申", "金"), ("戌", "土")]
        for i, (zhi, wx) in enumerate(expected):
            self.assertEqual(h.yaos[i].zhi, zhi, f"乾第{i+1}爻地支應為 {zhi}")
            self.assertEqual(h.yaos[i].wuxing, wx, f"乾第{i+1}爻五行應為 {wx}")
            self.assertEqual(ZHI_WUXING[h.yaos[i].zhi], wx)


# ============================================================================
# 5. 變爻六親（變後六親仍以本卦宮為我）
# ============================================================================
class TestBianYaoLiuqin(unittest.TestCase):
    """動爻變化後，變出的新地支六親仍以「本卦的宮五行」為我來判定"""

    def test_qian_chu_yao_dong_bian_to_xun(self):
        """乾卦初爻動（甲子水）→ 變姤 初爻 = 辛丑(土)
           乾宮金為我：土 → 父母（生我者）
        """
        h = annotate("111111", changing=[1])
        chu_yao = h.yaos[0]
        self.assertTrue(chu_yao.is_changing)
        self.assertEqual(chu_yao.liuqin, "子孫")       # 本爻甲子水 → 子孫
        self.assertEqual(chu_yao.bian_zhi, "丑")        # 變姤初爻 = 辛丑
        self.assertEqual(chu_yao.bian_wuxing, "土")
        self.assertEqual(chu_yao.bian_liuqin, "父母")   # 土生金 → 父母


if __name__ == "__main__":
    unittest.main(verbosity=2)
