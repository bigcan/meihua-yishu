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


class TestMeihuaDangXiangYingqi(unittest.TestCase):
    """v4.3：克體之黨、類象、應期依據（只整理，不下斷語）。"""

    def test_guanmei_ke_ti_faction(self):
        """觀梅占：「離火克之。互中巽木，復三起離火，則克體之卦氣盛。」"""
        r = mh._analyze_hexagram(2, 3, 1)
        line = next(x for x in r["生克之黨"] if x.startswith("克體之卦：離火"))
        self.assertIn("得巽木（互卦下）相生", line)
        self.assertTrue(any(x.startswith("生體之卦：艮土") and "被巽木" in x for x in r["生克之黨"]))

    def test_ji_bei_ming_faction(self):
        """雞悲鳴占：乾金為體，互離火克之，巽木生離火——「卦中巽木離火，有烹飪之象」。"""
        r = mh._analyze_hexagram(5, 1, 4)
        self.assertTrue(any(x.startswith("克體之卦：離火") and "得巽木" in x for x in r["生克之黨"]))

    def test_xiang_comes_from_reference_file(self):
        table = mh.load_bagua_xiang()
        self.assertEqual(set(table), set("乾兌離震巽坎艮坤"))
        self.assertIn("股", table["巽"]["身體"])          # 觀梅占「巽為股」
        self.assertIn("少女", table["兌"]["人物"])
        r = mh._analyze_hexagram(2, 3, 1)
        self.assertTrue(any(x.startswith("巽") and "股" in x for x in r["類象"]))

    def test_gua_number_timing(self):
        """老人有憂色占：乾一巽五加卯時四共十數，行中取半，斷五日。"""
        shiling = {"時令": "春", "月建": "卯", "近交節": False, "時支數": 4, "時支": "卯"}
        r = mh._analyze_hexagram(1, 5, 4, shiling)
        self.assertIn("＝10", r["應期"]["卦數"])
        self.assertIn("取半 5", r["應期"]["卦數"])
        self.assertIn("凶期（克體之卦氣）", r["應期"])      # 乾金克巽木之體
        self.assertNotIn("卦數", mh._analyze_hexagram(1, 5, 4).get("應期", {}))  # 無占時不猜


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


class TestVerdictRules(unittest.TestCase):
    """判斷層規則鏈：每條規則用《增刪卜易》一個卦例釘住（卦例見 tests/gold_zengshan.json）。

    每個測試都應在拿掉對應規則時轉紅。
    """

    ASK = {"世": "自身", "父母": "父母", "子孫": "子女", "妻財": "求財", "官鬼": "工作"}

    @classmethod
    def setUpClass(cls):
        import json
        path = os.path.join(HERE, "gold_zengshan.json")
        with open(path, encoding="utf-8") as f:
            cls.gold = {c["id"]: c for c in json.load(f)["cases"]}

    def run_case(self, cid, illness=None):
        c = self.gold[cid]
        h = nj.annotate(c["binary"], c["changing"], c["day"], c["month"])
        r = nj.find_yongshen(h, self.ASK[c["target"]], {"illness": illness} if illness else None)
        return h, r, r["verdict"]

    def test_true_void_only_when_month_controls(self):
        """旬空章：「旺不為空……真空即春土、夏金、秋木、三冬逢火。」"""
        h, _, v = self.run_case("ZS187")     # 申月，世爻亥水得月生而旬空 → 不為真空，出空得見
        self.assertTrue(h.shi().is_void)
        self.assertTrue(h.shi().void_kind.startswith("不為真空"))
        self.assertEqual(v["direction"], "吉")
        h, _, v = self.run_case("ZS083")     # 巳月，亥水財爻月破又空：「月破為空」「生之不起」
        self.assertTrue(h.yaos[4].void_kind.startswith("真空又月破"))
        self.assertEqual(v["direction"], "凶")

    def test_illness_recent_vs_chronic(self):
        """疾病章：久病逢六沖不治，近病逢之不藥而愈。"""
        _, _, v = self.run_case("ZS101", "近病")   # 占母近病得坤之剝，六沖
        self.assertEqual((v["direction"], v["rule"]), ("吉", "近病逢沖逢空"))
        _, _, v = self.run_case("ZS047", "久病")   # 久病得乾之夬，六沖
        self.assertEqual((v["direction"], v["rule"]), ("凶", "久病逢沖逢空"))
        _, _, v = self.run_case("ZS047")           # 不說病程就不套用此則
        self.assertNotEqual(v["rule"], "久病逢沖逢空")

    def test_shi_transforms_into_yongshen(self):
        """占財得未濟之鼎：「忌臨世位化酉財，即于酉日得財。」"""
        _, _, v = self.run_case("ZS079")
        self.assertEqual((v["direction"], v["rule"]), ("吉", "世化出用神"))

    def test_moving_line_generates_shi_and_shows_yongshen(self):
        """占財得兌之解：靜財空破，官動生世化出寅財——「神兆機于動」，寅日得財。"""
        _, _, v = self.run_case("ZS002")
        self.assertEqual((v["direction"], v["rule"]), ("吉", "動爻生世化出用神"))

    def test_fushen_usable_and_unusable(self):
        """飛伏神章：伏神得日月生者有用；休囚值月破者無用。"""
        _, r, v = self.run_case("ZS035")     # 候文書得賁：午火父伏而得卯月生，甲午日得
        self.assertIsNone(r["primary"])
        self.assertEqual((v["direction"], v["rule"]), ("吉", "伏神"))
        _, r, v = self.run_case("ZS141")     # 占功名得旅：官伏而月破，「勿想成名」
        self.assertIsNone(r["primary"])
        self.assertEqual((v["direction"], v["rule"]), ("凶", "伏神"))

    def test_rootless_yongshen(self):
        """自占病得大過之鼎：「用神無根，元神有力亦難生。」"""
        _, _, v = self.run_case("ZS003")
        self.assertEqual((v["direction"], v["rule"]), ("凶", "用神無根"))

    def test_huitou_ke_needs_force(self):
        """占病得謙之蹇：「雖化戌土之克，春令土衰，卯月克制，有殺無妨。」"""
        h, _, v = self.run_case("ZS087")
        self.assertFalse(nj._bian_has_force(h, h.shi()))
        self.assertEqual(v["direction"], "吉")
        h, _, v = self.run_case("ZS025")     # 比之井：世化酉金回頭沖克，變爻得申日扶 → 凶
        self.assertTrue(nj._bian_has_force(h, h.shi()))
        self.assertEqual(v["direction"], "凶")

    def test_line_on_day_branch_cannot_be_hurt(self):
        """日辰章：「諸爻不能傷日月。」借貸得晉，卯日即財，暗動之兄不能傷。"""
        _, r, v = self.run_case("ZS185")
        self.assertTrue(any("徒受其名" in e for e, _ in r["effects"]))
        self.assertEqual(v["direction"], "吉")

    def test_sanhe_waits_when_a_member_is_month_broken(self):
        """三合章：局中一爻空破，待填實之時方成局。艮之觀，午月子水月破。"""
        h, _, _ = self.run_case("ZS033")
        self.assertEqual(h.sanhe, [])
        self.assertTrue(any("局未成" in n for n in h.notes))

    def test_shi_month_broken(self):
        """求官章：「世空世破、官破官空，俱不得。」占復職得晉，世爻酉金月破。"""
        _, _, v = self.run_case("ZS093")
        self.assertEqual(v["direction"], "凶")
        self.assertTrue(any("世爻月破" in x for x in v["reasons"]))

    def test_metal_on_si_day_and_tomb_when_strong(self):
        """生旺墓絕章：金爻旺相逢巳日為長生，休囚則論克；旺相者入墓非真。"""
        h = nj.annotate("111111", [], "己巳", "辰")      # 辰月土生金：五爻申金旺相
        self.assertTrue(h.yaos[4].day_rel.startswith("日辰長生"))
        h = nj.annotate("111111", [], "己巳", "午")      # 午月火克金：休囚
        self.assertTrue(h.yaos[4].day_rel.startswith("日克"))
        h, _, _ = self.run_case("ZS058")                 # 申月辰日，亥水得月生而入日墓
        y = next(x for x in h.yaos if x.zhi == "亥")
        self.assertEqual(y.day_score, 0)

    def test_yingqi_main_candidate(self):
        """各門類應期總注章：每種狀態的主應期，各以一例釘住。"""
        for cid, want, why in (
            ("ZS035", "午", "伏神值日（候文書，甲午日得）"),
            ("ZS079", "酉", "世化出之財值日（酉日得財）"),
            ("ZS008", "子", "沖去回頭克之變爻（丙子日得見）"),
            ("ZS097", "申", "靜而逢沖（申日文書到）"),
            ("ZS043", "丑", "化進神逢值（丑日得差）"),
            ("ZS187", "亥", "旬空出旬填實（出空之日見官）"),
        ):
            h, r, _ = self.run_case(cid)
            cands = nj.yingqi_candidates(h, r)
            self.assertEqual(cands[0][0], want, f"{cid} {why}: {cands}")

    def test_yingqi_dates(self):
        """地支換西曆：2026-11-17 為乙未日，下一個辰日是 11/26；23 時起算次日。"""
        h = nj.annotate("111001", [2], "乙未", "亥")
        h.cast_at = datetime(2026, 11, 17, 14, 10)
        self.assertIn("辰日 11/26、12/08", nj._yingqi_dates(h, "辰"))
        self.assertIn("今日", nj._yingqi_dates(h, "未"))
        self.assertIn("辰月 2027/04/05", nj._yingqi_dates(h, "辰"))
        h = nj.annotate("111001", [2], "丙申", "亥")       # 11/17 23:30 已算丙申日
        h.cast_at = datetime(2026, 11, 17, 23, 30)
        self.assertIn("辰日 11/26", nj._yingqi_dates(h, "辰"))

    def test_every_dated_chart_gets_a_verdict(self):
        for cid in ("ZS035", "ZS141", "ZS184", "ZS186"):
            _, _, v = self.run_case(cid)
            self.assertIn(v["direction"], ("吉", "凶", "未定"))


nj.LIUQIN_KE_INV = lambda t: [k for k, v in nj.LIUQIN_KE.items() if v == t][0]

if __name__ == "__main__":
    unittest.main(verbosity=1)
