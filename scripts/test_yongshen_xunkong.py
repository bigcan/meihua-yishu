#!/usr/bin/env python3
"""
Tier 4：旬空 + 用神 + 沖合表 + 伏神單元測試

驗證項目：
  1. XUN_KONG 60 甲子六旬空亡表
     - 6 旬涵蓋全部 60 干支且無重複
     - 每旬 10 干支共用同 2 空支
     - 旬空計算規律：本旬未涵蓋的 2 地支即為空
  2. 五行 / 沖 / 合 / 三合表（基礎符號）
     - WUXING_SHENG / WUXING_KE 完整 5×5
     - LIU_CHONG 6 對 12 個雙向映射
     - LIU_HE 6 對 12 個雙向映射
     - SAN_HE 4 局（申子辰水、亥卯未木、寅午戌火、巳酉丑金）
  3. YONGSHEN_MAP 用神對照（《卜筮正宗》傳統分類）
     - 六親 5 大類核心映射
     - 男女問婚姻不同（女問取官鬼、男問取妻財）
     - 疾病以官鬼為病、子孫為藥
  4. find_yongshen 端到端
     - 用神上卦：返回對應六親爻列表
     - 用神不上卦：自動取本宮首卦伏神
  5. 旬空標註整合（annotate 端到端）
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from najia import (  # noqa: E402
    DIZHI,
    GANZHI_TO_XUNKONG,
    LIU_CHONG,
    LIU_HE,
    SAN_HE,
    TIANGAN,
    WUXING_KE,
    WUXING_SHENG,
    XUN_KONG,
    YONGSHEN_MAP,
    annotate,
    find_yongshen,
)


# ============================================================================
# 1. XUN_KONG 旬空表
# ============================================================================
class TestXunKong(unittest.TestCase):
    """六十甲子分六旬，各旬空 2 支"""

    EXPECTED_VOID = {
        "甲子": ["戌", "亥"],
        "甲戌": ["申", "酉"],
        "甲申": ["午", "未"],
        "甲午": ["辰", "巳"],
        "甲辰": ["寅", "卯"],
        "甲寅": ["子", "丑"],
    }

    def test_six_xun_heads(self):
        self.assertEqual(set(XUN_KONG.keys()), set(self.EXPECTED_VOID.keys()))

    def test_each_xun_has_ten_ganzhi(self):
        for xun_head, (gz_list, void) in XUN_KONG.items():
            self.assertEqual(len(gz_list), 10, f"{xun_head} 旬應有 10 干支")
            self.assertEqual(len(void), 2, f"{xun_head} 旬空應為 2 支")

    def test_void_zhi_correct(self):
        for xun_head, expected_void in self.EXPECTED_VOID.items():
            self.assertEqual(XUN_KONG[xun_head][1], expected_void)

    def test_total_60_ganzhi_unique(self):
        all_gz = [gz for (gz_list, _) in XUN_KONG.values() for gz in gz_list]
        self.assertEqual(len(all_gz), 60, "六旬合計應為 60 干支")
        self.assertEqual(len(set(all_gz)), 60, "60 干支不得重複")

    def test_void_rule_consistent(self):
        """每旬空支 = 12 地支中未被該旬 10 干支涵蓋的 2 支"""
        for xun_head, (gz_list, void) in XUN_KONG.items():
            zhi_in_xun = {gz[1] for gz in gz_list}
            zhi_not_in_xun = set(DIZHI) - zhi_in_xun
            self.assertEqual(set(void), zhi_not_in_xun,
                             f"{xun_head} 旬空計算與實際未涵蓋支不符")

    def test_ganzhi_to_xunkong_reverse_lookup(self):
        """60 干支每個都能查到旬空"""
        self.assertEqual(len(GANZHI_TO_XUNKONG), 60)

    def test_jiazi_day_void(self):
        """甲子日旬空戌亥（剛跑過的卦例）"""
        self.assertEqual(GANZHI_TO_XUNKONG["甲子"], ["戌", "亥"])

    def test_classical_examples(self):
        """抽樣若干干支對照空亡"""
        cases = [
            ("甲子", ["戌", "亥"]),
            ("乙丑", ["戌", "亥"]),  # 甲子旬
            ("癸酉", ["戌", "亥"]),  # 甲子旬尾
            ("甲戌", ["申", "酉"]),
            ("壬午", ["申", "酉"]),  # 甲戌旬
            ("庚寅", ["午", "未"]),  # 甲申旬
            ("辛丑", ["辰", "巳"]),  # 甲午旬
            ("庚戌", ["寅", "卯"]),  # 甲辰旬
            ("癸亥", ["子", "丑"]),  # 甲寅旬尾
        ]
        for gz, expected in cases:
            self.assertEqual(GANZHI_TO_XUNKONG[gz], expected,
                             f"{gz} 日旬空應為 {expected}")


# ============================================================================
# 2. 基礎五行 / 沖 / 合 / 三合表
# ============================================================================
class TestWuxingTables(unittest.TestCase):
    """五行生剋關係"""

    def test_sheng_chain(self):
        """木生火生土生金生水生木"""
        chain = ["木", "火", "土", "金", "水"]
        for i in range(5):
            self.assertEqual(WUXING_SHENG[chain[i]], chain[(i + 1) % 5])

    def test_ke_chain(self):
        """木剋土剋水剋火剋金剋木"""
        chain = ["木", "土", "水", "火", "金"]
        for i in range(5):
            self.assertEqual(WUXING_KE[chain[i]], chain[(i + 1) % 5])

    def test_complete_coverage(self):
        for wx in ["木", "火", "土", "金", "水"]:
            self.assertIn(wx, WUXING_SHENG)
            self.assertIn(wx, WUXING_KE)


class TestLiuChong(unittest.TestCase):
    """六沖：子午、丑未、寅申、卯酉、辰戌、巳亥"""

    PAIRS = [("子", "午"), ("丑", "未"), ("寅", "申"),
             ("卯", "酉"), ("辰", "戌"), ("巳", "亥")]

    def test_six_pairs_bidirectional(self):
        for a, b in self.PAIRS:
            self.assertEqual(LIU_CHONG[a], b, f"{a} 沖 {b}")
            self.assertEqual(LIU_CHONG[b], a, f"{b} 沖 {a}")

    def test_complete_12_entries(self):
        self.assertEqual(len(LIU_CHONG), 12)


class TestLiuHe(unittest.TestCase):
    """六合：子丑、寅亥、卯戌、辰酉、巳申、午未"""

    PAIRS = [("子", "丑"), ("寅", "亥"), ("卯", "戌"),
             ("辰", "酉"), ("巳", "申"), ("午", "未")]

    def test_six_pairs_bidirectional(self):
        for a, b in self.PAIRS:
            self.assertEqual(LIU_HE[a], b, f"{a} 合 {b}")
            self.assertEqual(LIU_HE[b], a, f"{b} 合 {a}")

    def test_complete_12_entries(self):
        self.assertEqual(len(LIU_HE), 12)


class TestSanHe(unittest.TestCase):
    """三合：申子辰水、亥卯未木、寅午戌火、巳酉丑金"""

    EXPECTED = {
        frozenset(["申", "子", "辰"]): "水局",
        frozenset(["亥", "卯", "未"]): "木局",
        frozenset(["寅", "午", "戌"]): "火局",
        frozenset(["巳", "酉", "丑"]): "金局",
    }

    def test_four_combinations(self):
        self.assertEqual(SAN_HE, self.EXPECTED)


class TestTianganDizhi(unittest.TestCase):
    """干支基本常數"""

    def test_tiangan_length(self):
        self.assertEqual(len(TIANGAN), 10)
        self.assertEqual(TIANGAN[0], "甲")
        self.assertEqual(TIANGAN[-1], "癸")

    def test_dizhi_length(self):
        self.assertEqual(len(DIZHI), 12)
        self.assertEqual(DIZHI[0], "子")
        self.assertEqual(DIZHI[-1], "亥")


# ============================================================================
# 3. YONGSHEN_MAP 用神對照
# ============================================================================
class TestYongshenMap(unittest.TestCase):
    """《卜筮正宗》傳統用神分類"""

    # 各六親至少必須涵蓋的核心問事類型
    CORE_MAPPINGS = {
        "兄弟": ["自身", "兄弟", "朋友", "同事", "競爭對手"],
        "父母": ["父母", "長輩", "房屋", "車輛", "文書", "契約", "學業"],
        "子孫": ["子女", "晚輩", "六畜", "藥物", "醫生"],
        "妻財": ["妻子", "財物", "錢財", "薪資", "求財", "買賣"],
        "官鬼": ["丈夫", "工作", "事業", "官位", "功名", "考試", "疾病", "訴訟", "盜賊"],
    }

    def test_core_mappings(self):
        for liuqin, question_list in self.CORE_MAPPINGS.items():
            for q in question_list:
                self.assertIn(q, YONGSHEN_MAP, f"問事類型「{q}」應在 YONGSHEN_MAP 中")
                self.assertEqual(
                    YONGSHEN_MAP[q], liuqin,
                    f"問事「{q}」用神應為「{liuqin}」，實得「{YONGSHEN_MAP.get(q)}」"
                )

    def test_marriage_gender_distinct(self):
        """婚姻問事性別不同：女問取官鬼（丈夫）、男問取妻財（妻子）"""
        self.assertEqual(YONGSHEN_MAP["妻子"], "妻財")
        self.assertEqual(YONGSHEN_MAP["丈夫"], "官鬼")
        self.assertEqual(YONGSHEN_MAP["情人（女）"], "妻財")
        self.assertEqual(YONGSHEN_MAP["情人（男）"], "官鬼")

    def test_illness_uses_guan_gui(self):
        """占病以官鬼為用神（病），子孫為藥（醫）"""
        self.assertEqual(YONGSHEN_MAP["疾病"], "官鬼")
        self.assertEqual(YONGSHEN_MAP["藥物"], "子孫")
        self.assertEqual(YONGSHEN_MAP["醫生"], "子孫")

    def test_examination_uses_guan_gui(self):
        """考試/功名/官位用官鬼"""
        for q in ["考試", "功名", "官位", "升遷"]:
            self.assertEqual(YONGSHEN_MAP[q], "官鬼")

    def test_property_uses_fu_mu(self):
        """房屋、車輛、文書、契約皆用父母"""
        for q in ["房屋", "車輛", "船車", "文書", "契約"]:
            self.assertEqual(YONGSHEN_MAP[q], "父母")


# ============================================================================
# 4. find_yongshen 端到端
# ============================================================================
class TestFindYongshen(unittest.TestCase):
    """整合測試：annotate + find_yongshen"""

    def test_xun_wei_feng_qiu_cai(self):
        """巽為風求財 → 找妻財，應找到第1爻辛丑、第4爻辛未"""
        h = annotate("110110")
        result = find_yongshen(h, "求財")
        self.assertEqual(result["liuqin"], "妻財")
        positions = sorted(y.position for y in result["yaos"])
        self.assertEqual(positions, [1, 4])
        ganzhis = sorted(y.ganzhi() for y in result["yaos"])
        self.assertEqual(ganzhis, ["辛丑", "辛未"])
        self.assertIsNone(result["fushen"], "用神已上卦，不需要伏神")

    def test_qian_wei_tian_gong_zuo(self):
        """乾為天問工作 → 找官鬼，應找到第4爻壬午"""
        h = annotate("111111")
        result = find_yongshen(h, "工作")
        self.assertEqual(result["liuqin"], "官鬼")
        positions = [y.position for y in result["yaos"]]
        self.assertEqual(positions, [4])
        self.assertEqual(result["yaos"][0].ganzhi(), "壬午")

    def test_unknown_question_type(self):
        h = annotate("111111")
        result = find_yongshen(h, "不存在的類型XYZ")
        self.assertIn("error", result)


# ============================================================================
# 5. 伏神：用神不上卦時取本宮首卦對應爻
# ============================================================================
class TestFushen(unittest.TestCase):
    """
    天地否（乾宮三世）= 111000
    下三爻 = 坤[:3] = [乙未(土), 乙巳(火), 乙卯(木)]
    上三爻 = 乾[3:] = [壬午(火), 壬申(金), 壬戌(土)]
    爻五行: [土, 火, 木, 火, 金, 土]
    乾宮金為我：
      兄弟=金(1), 父母=土(2), 官鬼=火(2), 妻財=木(1), 子孫=水(0) ← 缺
    求子孫應取本宮首卦伏神：
      乾首卦 = [甲子(水), 甲寅(木), ...] → 第1爻甲子水 = 子孫（伏神）
    """

    def test_pi_gua_zi_sun_fushen(self):
        h = annotate("111000")
        self.assertEqual(h.hex_name, "天地否")
        self.assertEqual(h.palace_name, "乾")
        # 確認本卦無子孫
        zi_sun_in_hex = [y for y in h.yaos if y.liuqin == "子孫"]
        self.assertEqual(zi_sun_in_hex, [], "天地否本卦應無子孫")

        result = find_yongshen(h, "子女")
        self.assertEqual(result["liuqin"], "子孫")
        self.assertEqual(result["yaos"], [])
        self.assertIsNotNone(result["fushen"], "子孫不上卦應有伏神")
        fushen = result["fushen"]
        self.assertEqual(fushen["position"], 1)
        self.assertEqual(fushen["ganzhi"], "甲子")
        self.assertEqual(fushen["wuxing"], "水")
        self.assertEqual(fushen["liuqin"], "子孫")


# ============================================================================
# 6. 旬空標註整合
# ============================================================================
class TestXunKongAnnotation(unittest.TestCase):
    """annotate(day_ganzhi=...) 應正確標註空亡爻"""

    def test_xun_wei_feng_jiazi_day(self):
        """巽為風 + 甲子日：第2爻辛亥旬空（甲子旬空戌亥）"""
        h = annotate("110110", day_ganzhi="甲子")
        # 第2爻 = 辛亥
        self.assertEqual(h.yaos[1].ganzhi(), "辛亥")
        self.assertTrue(h.yaos[1].is_void, "辛亥日旬空（甲子旬空戌亥）")
        # 其他爻不應旬空（純巽爻支為丑亥酉未巳卯，僅亥在空）
        non_void_zhi = ["丑", "酉", "未", "巳", "卯"]
        for y in h.yaos:
            if y.zhi in non_void_zhi:
                self.assertFalse(y.is_void, f"第{y.position}爻 {y.zhi} 不應旬空")

    def test_jiazi_day_he_chong(self):
        """巽為風 + 甲子日：第1爻辛丑與日支子相合"""
        h = annotate("110110", day_ganzhi="甲子")
        self.assertTrue(h.yaos[0].is_ri_he, "辛丑與甲子日支子相合")
        # 第5爻辛巳不應日合（巳合申，子不合巳）
        self.assertFalse(h.yaos[4].is_ri_he)


if __name__ == "__main__":
    unittest.main(verbosity=2)
