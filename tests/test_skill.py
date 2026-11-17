#!/usr/bin/env python3
"""
回歸測試：python3 tests/test_skill.py （或 pytest tests/）

涵蓋：農曆轉換、節氣月建、日干支、梅花原書案例、納甲裝卦、世應、
伏吟反吟、三合、旬空真假、日沖暗動／日破、用神取捨、策略表變卦路徑。
"""

import os
import sys
import unittest
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import calendar_util as cal  # noqa: E402
import meihua_calc as mh  # noqa: E402
import najia as nj  # noqa: E402


class TestCalendar(unittest.TestCase):
    def test_lunar_known_dates(self):
        cases = {
            (2024, 2, 10): (2024, 1, 1, False),   # 甲辰春節
            (2025, 1, 29): (2025, 1, 1, False),
            (2026, 2, 17): (2026, 1, 1, False),
            (2025, 10, 6): (2025, 8, 15, False),  # 中秋
            (2023, 3, 22): (2023, 2, 1, True),    # 閏二月初一
            (2026, 10, 12): (2026, 9, 3, False),
        }
        for g, l in cases.items():
            self.assertEqual(mh.gregorian_to_lunar(*g), l, g)

    def test_lunar_roundtrip(self):
        for g in [(2024, 2, 10), (2023, 4, 19), (2023, 4, 20), (2033, 12, 22), (2099, 12, 31)]:
            ly, lm, ld, leap = mh.gregorian_to_lunar(*g)
            self.assertEqual(mh.lunar_to_gregorian(ly, lm, ld, leap).timetuple()[:3], g)

    def test_day_ganzhi(self):
        self.assertEqual(cal.day_ganzhi(datetime(2000, 1, 1, 12))[0], "戊午")
        self.assertEqual(cal.day_ganzhi(datetime(2026, 10, 12, 16))[0], "己未")
        # 23 時起算次日
        self.assertEqual(cal.day_ganzhi(datetime(2026, 10, 12, 23))[0], "庚申")

    def test_month_by_solar_term(self):
        # 2024 立春：2/4 16:27（UTC+8）
        self.assertEqual(cal.month_zhi(datetime(2024, 2, 4, 15, 50))[0], "丑")
        self.assertEqual(cal.month_zhi(datetime(2024, 2, 4, 17, 0))[0], "寅")
        # 2026 寒露約 10/8 → 10/12 已是戌月
        self.assertEqual(cal.month_zhi(datetime(2026, 10, 12, 16))[0], "戌")
        p = cal.pillars(datetime(2026, 10, 12, 16, 25))
        self.assertEqual((p["年"], p["月"], p["日"]), ("丙午", "戊戌", "己未"))

    def test_year_lichun_boundary(self):
        self.assertEqual(cal.year_ganzhi_lichun(datetime(2024, 2, 4, 15)), "癸卯")
        self.assertEqual(cal.year_ganzhi_lichun(datetime(2024, 2, 4, 18)), "甲辰")


class TestMeihua(unittest.TestCase):
    def test_guanmei(self):
        """觀梅占：辰年十二月十七日申時 → 澤火革，初爻動，變澤山咸，互乾巽。"""
        r = mh.qigua_by_time(2024, 12, 17, 15)
        self.assertEqual(r["本卦"]["名稱"], "澤火革")
        self.assertEqual(r["本卦"]["動爻位"], 1)
        self.assertEqual(r["變卦"]["名稱"], "澤山咸")
        self.assertEqual((r["互卦"]["上互"], r["互卦"]["下互"]), ("乾", "巽"))
        self.assertIn("兌", r["體用"]["體卦"])

    def test_mudan(self):
        """牡丹占：巳年三月十六日卯時 → 天風姤，五爻動，變火風鼎。"""
        r = mh.qigua_by_time(2025, 3, 16, 6)
        self.assertEqual(r["本卦"]["名稱"], "天風姤")
        self.assertEqual(r["本卦"]["動爻位"], 5)
        self.assertEqual(r["變卦"]["名稱"], "火風鼎")
        self.assertIn("乾", r["體用"]["用卦"])

    def test_qian_kun_hu_from_bian(self):
        r = mh.qigua_by_numbers(1, 1)  # 乾為天，動爻 2
        self.assertTrue(r["互卦"]["取自變卦"])

    def test_season_tu_month(self):
        """坤艮旺於辰戌丑未月（整月），非季末 18 天。"""
        r = mh.qigua_by_gregorian_time(2026, 10, 12, 16)
        self.assertIn("戌月", r["卦氣旺衰"]["時令"])
        self.assertEqual(mh.analyze_wangshuai("土", "土月"), "旺")
        self.assertEqual(mh.analyze_wangshuai("水", "土月"), "死")
        self.assertEqual(mh.analyze_wangshuai("金", "土月"), "相")

    def test_zishi_rollover(self):
        r = mh.qigua_by_gregorian_time(2026, 10, 12, 23)
        self.assertIn("子時推日", r["計算過程"])
        self.assertEqual(r["計算過程"]["日數"], 4)

    def test_number_total_mod6(self):
        r = mh.qigua_by_numbers(6, 8, 9)
        self.assertEqual(r["本卦"]["動爻位"], (6 + 8 + 9) % 6 or 6)
        r2 = mh.qigua_by_numbers(6, 8, None, None, add_hour=9)
        self.assertEqual(r2["本卦"]["動爻位"], (6 + 8 + 9) % 6 or 6)

    def test_strategy_paths_valid(self):
        """策略表每條「X → Y（變N爻」都要真的能由 X 變 N 爻得到 Y。"""
        import re
        short = {}
        bins = {}
        for (u, l), (num, name) in mh.HEXAGRAMS.items():
            s_ = name[0] if "為" in name else name[2:]
            short[s_] = num
            bins[num] = mh.get_hexagram_binary(u, l)
        for num, (_, _, _, path) in mh.HEXAGRAM_STRATEGY.items():
            if not path:
                continue
            m = re.match(r"(\S+) → (\S+?)（變(\d)爻", path)
            self.assertIsNotNone(m, path)
            src, dst, n = m.group(1), m.group(2), int(m.group(3))
            self.assertEqual(short[src], num, path)
            got = mh.apply_change(bins[num], n)
            self.assertEqual(got, bins[short[dst]], path)


class TestNajia(unittest.TestCase):
    def test_qian_zhuangua(self):
        h = nj.annotate("111111")
        self.assertEqual([y.ganzhi() for y in h.yaos], ["甲子", "甲寅", "甲辰", "壬午", "壬申", "壬戌"])
        self.assertEqual([y.liuqin for y in h.yaos], ["子孫", "妻財", "父母", "官鬼", "兄弟", "父母"])
        self.assertEqual((h.shi_pos, h.ying_pos), (6, 3))

    def test_palace_and_shi(self):
        h = nj.annotate("111001")  # 天雷无妄
        self.assertEqual((h.palace_name, h.generation_name, h.shi_pos, h.ying_pos), ("巽", "四世", 4, 1))
        h = nj.annotate("000010")  # 地水師：坎宮歸魂，世三應上
        self.assertEqual((h.palace_name, h.generation_name, h.shi_pos, h.ying_pos), ("坎", "歸魂", 3, 6))

    def test_every_hexagram_has_palace(self):
        self.assertEqual(len(nj.HEX_TO_PALACE), 64)

    def test_xunkong(self):
        self.assertEqual(nj.xunkong("甲子"), ["戌", "亥"])
        self.assertEqual(nj.xunkong("己未"), ["子", "丑"])
        self.assertEqual(nj.xunkong("癸亥"), ["子", "丑"])

    def test_fuyin_only_when_trigram_changes(self):
        h = nj.annotate("111111", [5, 6])          # 外卦乾→震
        self.assertTrue(any("伏吟" in n for n in h.notes))
        h = nj.annotate("111111", [1])             # 單動，不應誤報伏吟
        self.assertFalse(any("伏吟" in n for n in h.notes))
        h = nj.annotate("000000", [2, 3])          # 內卦坤→巽，未丑巳亥卯酉逐一相沖
        self.assertTrue(any("爻反吟" in n for n in h.notes))

    def test_sanhe_needs_moving(self):
        h = nj.annotate("111001")  # 無動爻：子辰申靜，不成局
        self.assertEqual(h.sanhe, [])

    def test_an_dong_vs_ri_po(self):
        # 无妄四爻午火，戌月（火生土=洩）子日沖：休囚 → 日破
        h = nj.annotate("111001", [], "甲子", "戌")
        self.assertTrue(h.yaos[3].is_ri_po)
        # 同爻在巳月（臨月扶）子日沖：旺相 → 暗動
        h = nj.annotate("111001", [], "甲子", "巳")
        self.assertTrue(h.yaos[3].is_an_dong)
        self.assertFalse(h.yaos[3].is_ri_po)

    def test_void_kind(self):
        h = nj.annotate("111001", [], "己未", "戌")  # 初爻子水：月克日克靜空 → 真空
        self.assertTrue(h.yaos[0].void_kind.startswith("真空"))
        h = nj.annotate("111001", [1], "己未", "戌")  # 動空不為空
        self.assertTrue(h.yaos[0].void_kind.startswith("不為真空"))

    def test_change_notes(self):
        h = nj.annotate("111001", [2, 6], "己未", "戌")
        self.assertTrue(any("進神" in n for n in h.yaos[1].change_notes))   # 寅化卯
        self.assertTrue(any("退神" in n for n in h.yaos[5].change_notes))   # 戌化未

    def test_tu_jin_shen_cycle(self):
        self.assertIn(("戌", "丑"), nj.JIN_SHEN)
        self.assertIn(("丑", "戌"), nj.TUI_SHEN)

    def test_ambiguous_ask(self):
        h = nj.annotate("111001", [2], "己未", "戌")
        self.assertIn("error", nj.find_yongshen(h, "婚姻"))

    def test_yongshen_rank_and_self(self):
        h = nj.annotate("111001", [2, 6], "己未", "戌")
        r = nj.find_yongshen(h, "求財")
        self.assertEqual(r["primary"].position, 6)  # 兩現取動
        r = nj.find_yongshen(h, "自身")
        self.assertEqual(r["primary"].position, h.shi_pos)
        self.assertEqual(r["jishen"][0], nj.LIUQIN_KE_INV(r["target_liuqin"]))

    def test_fushen(self):
        h = nj.annotate("111110")  # 天風姤：辛丑 辛亥 辛酉 壬午 壬申 壬戌
        r = nj.find_yongshen(h, "求財")
        self.assertIsNone(r["primary"])
        self.assertEqual(r["fushen"]["ganzhi"], "甲寅")


nj.LIUQIN_KE_INV = lambda t: [k for k, v in nj.LIUQIN_KE.items() if v == t][0]

if __name__ == "__main__":
    unittest.main(verbosity=1)
