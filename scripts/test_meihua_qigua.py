#!/usr/bin/env python3
"""
Tier 6：梅花易數起卦端到端單元測試

驗證項目：
  1. num_to_gua / num_to_yao 餘 0 邊界（餘 0 當 8 / 餘 0 當 6）
  2. qigua_by_numbers：兩數起卦、三數起卦（動爻取總數除六）
  3. qigua_by_time：邵子《梅花易數》觀梅占經典案例
     - 辰年十二月十七日申時 → 澤火革，初爻動，互天風姤，變澤山咸
     - 體兌金，用離火，火剋金 = 用剋體（凶）
  4. qigua_by_gregorian_time：西曆→農曆→起卦端到端
  5. 體用判定方向（動爻 ≤ 3 上為體；> 3 下為體）
  6. 乾為天／坤為地互卦取自變卦
  7. 日始於子時：23 時推次日（含月末、年末、閏月轉入）

整條梅花起卦線（時間/數字/西曆）與已驗證的農曆+八卦+動爻數整合驗證。
"""

from __future__ import annotations

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from meihua_calc import (  # noqa: E402
    BAGUA,
    DIZHI,
    GUADE_INTENT,
    HEXAGRAMS,
    SEASON_ELEMENT,
    YEAR_INFOS,
    _analyze_hexagram,
    _month_days,
    _MONTH_SEASON,
    _yao_name,
    analyze_guade,
    analyze_wangshuai,
    analyze_wuxing,
    analyze_yao_positions,
    binary_to_gua_pair,
    get_cuo_gua,
    get_hexagram_binary,
    get_season,
    get_year_dizhi,
    get_zong_gua,
    lunar_next_day,
    num_to_gua,
    num_to_yao,
    qigua_by_gregorian_time,
    qigua_by_gregorian_time_precise,
    qigua_by_numbers,
    qigua_by_numbers_at,
    qigua_by_time,
    qigua_by_time_precise,
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

    def test_three_numbers_total_over_six(self):
        """6, 8, 3 → 上坎下坤，動爻取總數除六 = (6+8+3)%6 = 5

        原書三數起卦的動爻是總數除六，不是只取第三數（那是今人簡法）。
        """
        result = qigua_by_numbers(6, 8, 3)
        self.assertEqual(result["本卦"]["名稱"], "水地比")
        self.assertEqual(result["本卦"]["動爻"], "第5爻")
        self.assertIn("(6+8+3)", result["計算過程"]["動爻"])

    def test_three_numbers_not_third_alone(self):
        """回歸測試：動爻不得退回「只取第三數除六」的簡法。

        選 num3 使兩種算法給出不同結果：只取第三數 → 4%6=4；
        總數除六 → (1+1+4)%6=6。
        """
        result = qigua_by_numbers(1, 1, 4)
        self.assertEqual(result["本卦"]["動爻"], "第6爻")

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
                result = _analyze_hexagram(1, 8, dong)  # 上乾 下坤
                self.assertTrue(result["體用"]["體卦"].startswith("乾"),
                                f"動爻 {dong} 在下，上卦乾應為體，實得 {result['體用']['體卦']}")

    def test_dong_in_upper_lower_is_ti(self):
        """動爻 4, 5, 6 → 動在上卦 → 下卦為體"""
        for dong in [4, 5, 6]:
            with self.subTest(dong=dong):
                result = _analyze_hexagram(1, 8, dong)  # 上乾 下坤
                self.assertTrue(result["體用"]["體卦"].startswith("坤"),
                                f"動爻 {dong} 在上，下卦坤應為體，實得 {result['體用']['體卦']}")


# ============================================================================
# 4a. 體用五行生剋（梅花易數最核心的判斷規則）
# ============================================================================
class TestAnalyzeWuxing(unittest.TestCase):
    """先前只有觀梅占間接斷言過「用克體」一種，其餘四種關係無任何測試。
    體用生剋是整個梅花系統用得最多的規則，五種關係逐一釘死。"""

    # (體五行, 用五行) → 應得關係
    CASES = [
        ("木", "木", "比和（吉）"),
        ("金", "金", "比和（吉）"),
        ("木", "水", "用生體（大吉）"),   # 水生木
        ("火", "木", "用生體（大吉）"),   # 木生火
        ("木", "火", "體生用（耗洩）"),   # 木生火，體洩氣
        ("水", "木", "體生用（耗洩）"),
        ("木", "土", "體克用（吉）"),     # 木剋土
        ("金", "木", "體克用（吉）"),
        ("木", "金", "用克體（凶）"),     # 金剋木
        ("土", "木", "用克體（凶）"),
    ]

    def test_all_five_relations(self):
        for ti, yong, expected in self.CASES:
            with self.subTest(體=ti, 用=yong):
                self.assertEqual(analyze_wuxing(ti, yong), expected)

    def test_every_element_pair_is_classified(self):
        """25 種組合都必須落入五種關係之一，不得出現「未知關係」"""
        elements = ["木", "火", "土", "金", "水"]
        relations = set()
        for ti in elements:
            for yong in elements:
                got = analyze_wuxing(ti, yong)
                self.assertNotEqual(got, "未知關係", f"體{ti}用{yong} 未被分類")
                relations.add(got)
        self.assertEqual(len(relations), 5, f"應恰好五種關係，實得 {relations}")

    def test_sheng_ke_directions_are_not_mirrored(self):
        """生剋有方向：體生用與用生體不可互換，體克用與用克體不可互換。
        防止 analyze_wuxing 的比較方向被鏡像翻轉。"""
        self.assertNotEqual(analyze_wuxing("木", "火"), analyze_wuxing("火", "木"))
        self.assertNotEqual(analyze_wuxing("木", "土"), analyze_wuxing("土", "木"))


# ============================================================================
# 4a-2. 卦氣旺衰（推導 ↔ 兩份 markdown 表同步）
# ============================================================================
class TestWangShuai(unittest.TestCase):
    """旺衰改為推導（當令旺／令生相／生令休／剋令囚／令剋死），不再存表。
    yingqi-calc.md §3.1 與 ying-guides.md 第四應各有一份人類可讀的表，
    本測試逐格比對推導結果與那兩份表——三者任一被單方面修改就失敗。"""

    REF_DIR = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "references")
    GUA_ELEMENT = {"震巽": "木", "離": "火", "坤艮": "土", "乾兌": "金", "坎": "水"}

    def test_derivation_matches_yingqi_calc_table(self):
        """yingqi-calc.md §3.1 完整五態表：季節|旺五行|旺卦|相卦|休卦|囚卦|死卦"""
        path = os.path.join(self.REF_DIR, "yingqi-calc.md")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()

        rows = re.findall(
            r"^(春|夏|秋|冬|四季末)\|(木|火|土|金|水)\|(\S+)\|(\S+)\|(\S+)\|(\S+)\|(\S+)\s*$",
            text, re.M)
        self.assertEqual(len(rows), 5, f"§3.1 應有 5 季，實得 {len(rows)}")

        cells = 0
        for season, ruling, *states in rows:
            self.assertEqual(
                SEASON_ELEMENT[season], ruling,
                f"{season} 當旺五行：程式 {SEASON_ELEMENT[season]} vs 表 {ruling}")
            for expected_state, gua in zip(["旺", "相", "休", "囚", "死"], states):
                element = self.GUA_ELEMENT[gua]
                got = analyze_wangshuai(element, season)
                self.assertEqual(
                    got, expected_state,
                    f"{season}·{gua}({element})：推導得「{got}」，"
                    f"但 yingqi-calc.md §3.1 標為「{expected_state}」")
                cells += 1
        self.assertEqual(cells, 25, "5 季 × 5 態應為 25 格")

    def test_derivation_matches_ying_guides_table(self):
        """ying-guides.md 第四應只列兩極：季節 旺相之卦 休囚之卦（實為死）"""
        path = os.path.join(self.REF_DIR, "ying-guides.md")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()

        rows = re.findall(
            r"^(春|夏|秋|冬|四季末) (\S+)（(?:木|火|土|金|水)旺） (\S+)（(?:木|火|土|金|水)死）\s*$",
            text, re.M)
        self.assertEqual(len(rows), 5, f"第四應時令表應有 5 季，實得 {len(rows)}")
        for season, wang_gua, si_gua in rows:
            self.assertEqual(analyze_wangshuai(self.GUA_ELEMENT[wang_gua], season), "旺",
                             f"{season}·{wang_gua} 應為旺")
            self.assertEqual(analyze_wangshuai(self.GUA_ELEMENT[si_gua], season), "死",
                             f"{season}·{si_gua} 應為死")

    def test_each_season_assigns_all_five_states_once(self):
        for season in SEASON_ELEMENT:
            with self.subTest(season=season):
                states = [analyze_wangshuai(e, season)
                          for e in ["木", "火", "土", "金", "水"]]
                self.assertEqual(sorted(states), sorted(["旺", "相", "休", "囚", "死"]),
                                 f"{season} 五行狀態分配錯誤：{states}")

    def test_sijimo_is_last_18_days(self):
        """四季末＝農曆三、六、九、十二月的最後18天；缺了它土永不當令"""
        info = YEAR_INFOS[2024 - 1900]
        for month in (3, 6, 9, 12):
            length = _month_days(info, month, False)
            with self.subTest(month=month):
                self.assertEqual(get_season(2024, month, length - 18), _MONTH_SEASON[month])
                self.assertEqual(get_season(2024, month, length - 17), "四季末")
                self.assertEqual(get_season(2024, month, length), "四季末")

    def test_non_earth_months_never_sijimo(self):
        for month in (1, 2, 4, 5, 7, 8, 10, 11):
            for day in (1, 15, 29):
                self.assertEqual(get_season(2024, month, day), _MONTH_SEASON[month])

    def test_time_cast_emits_wangshuai_number_cast_does_not(self):
        """數字起卦無日期→無時令，該節必須從缺（猜today是捏造）"""
        timed = qigua_by_time(2024, 1, 15, 10)
        self.assertIn("卦氣旺衰", timed)
        self.assertIn("春", timed["卦氣旺衰"]["時令"])
        self.assertNotIn("卦氣旺衰", qigua_by_numbers(6, 8))

    def test_ti_de_ling_flag_matches_state(self):
        for y, m, d in [(2024, 1, 15), (2024, 5, 10), (2024, 8, 3), (2024, 11, 20)]:
            result = qigua_by_time(y, m, d, 10)
            ws = result["卦氣旺衰"]
            with self.subTest(date=(y, m, d)):
                self.assertEqual(ws["體卦得令"],
                                 ws["體卦旺衰"].endswith(("旺", "相")))


# ============================================================================
# 4a-3. 錯卦／綜卦（卦變之學，非原書梅花法，屬本專案加掛透鏡）
# ============================================================================
class TestCuoZongGua(unittest.TestCase):

    def test_cuo_is_full_yinyang_flip(self):
        self.assertEqual(get_cuo_gua("111111"), binary_to_gua_pair("000000"))
        self.assertEqual(get_cuo_gua("010101"), binary_to_gua_pair("101010"))

    def test_zong_is_vertical_reversal(self):
        # 屯(010001) 顛倒為 蒙(100010)——屯蒙為經典綜卦對
        self.assertEqual(get_zong_gua("010001"), binary_to_gua_pair("100010"))

    def test_both_are_involutions(self):
        """錯之錯、綜之綜都應回到本卦——防止翻轉方向被改成別的操作"""
        for (u, ln), (num, _name) in HEXAGRAMS.items():
            binary = get_hexagram_binary(u, ln)
            with self.subTest(hexagram=num):
                cuo = get_hexagram_binary(*get_cuo_gua(binary))
                self.assertEqual(get_hexagram_binary(*get_cuo_gua(cuo)), binary)
                zong = get_hexagram_binary(*get_zong_gua(binary))
                self.assertEqual(get_hexagram_binary(*get_zong_gua(zong)), binary)

    def test_qian_kun_jiji_weiji_pairs(self):
        result = _analyze_hexagram(1, 1, 1)          # 乾為天
        self.assertEqual(result["錯卦"]["名稱"], "坤為地")
        jiji = _analyze_hexagram(6, 3, 1)            # 水火既濟（坎上離下）
        self.assertEqual(jiji["本卦"]["名稱"], "水火既濟")
        self.assertEqual(jiji["錯卦"]["名稱"], "火水未濟")
        self.assertEqual(jiji["綜卦"]["名稱"], "火水未濟")


# ============================================================================
# 4a-4. 爻位盤（《周易》義理爻位學：當位／得中／應／承乘）
# ============================================================================
class TestYaoPositions(unittest.TestCase):
    """既濟六爻皆當位、未濟六爻皆失正，是爻位學最經典的一對錨點。"""

    def test_jiji_all_correct_positions(self):
        board = analyze_yao_positions("010101", 1)   # 水火既濟
        self.assertTrue(all(ln["當位"] == "得正" for ln in board["六爻"]),
                        [ln["當位"] for ln in board["六爻"]])
        self.assertTrue(all(ln["有應"] for ln in board["六爻"]),
                        "既濟六爻皆相應")
        self.assertTrue(board["二五中正相應"])

    def test_weiji_all_incorrect_positions(self):
        board = analyze_yao_positions("101010", 1)   # 火水未濟
        self.assertTrue(all(ln["當位"] == "失正" for ln in board["六爻"]),
                        [ln["當位"] for ln in board["六爻"]])
        self.assertFalse(board["二五中正相應"])

    def test_yao_names(self):
        self.assertEqual(_yao_name(1, True), "初九")
        self.assertEqual(_yao_name(1, False), "初六")
        self.assertEqual(_yao_name(6, True), "上九")
        self.assertEqual(_yao_name(6, False), "上六")
        self.assertEqual(_yao_name(2, False), "六二")
        self.assertEqual(_yao_name(5, True), "九五")

    def test_names_match_yinyang_of_binary(self):
        """爻名的九/六必須跟著該位的陰陽走（初爻為最右位元）"""
        board = analyze_yao_positions("010101", 1)
        got = [ln["名稱"] for ln in board["六爻"]]
        self.assertEqual(got, ["初九", "六二", "九三", "六四", "九五", "上六"])

    def test_zhong_only_at_two_and_five(self):
        board = analyze_yao_positions("110101", 3)
        for ln in board["六爻"]:
            with self.subTest(位=ln["位"]):
                self.assertEqual(ln["得中"] == "得中", ln["位"] in (2, 5))

    def test_ying_partners_are_1_4__2_5__3_6(self):
        board = analyze_yao_positions("110101", 3)
        self.assertEqual([ln["應位"] for ln in board["六爻"]], [4, 5, 6, 1, 2, 3])

    def test_chengcheng_terminology(self):
        """古法「乘」專指陰居陽上；反向是下陰承陽。不得出現自創的「陽乘陰」。"""
        board = analyze_yao_positions("110101", 3)   # 風火家人
        marks = [ln["承乘"] for ln in board["六爻"] if ln["承乘"]]
        self.assertTrue(marks)
        for m in marks:
            self.assertIn(m.split("（")[0], ("陰乘陽", "下陰承陽"))
        self.assertNotIn("陽乘陰", "".join(marks))

    def test_chengcheng_direction(self):
        """陰爻在上、陽爻在下 → 該陰爻標陰乘陽；反之標下陰承陽"""
        board = analyze_yao_positions("110101", 3)   # 初九 六二 九三 六四 九五 上九
        by_pos = {ln["位"]: ln["承乘"] for ln in board["六爻"]}
        self.assertTrue(by_pos[2].startswith("陰乘陽"))     # 六二 乘 初九
        self.assertTrue(by_pos[3].startswith("下陰承陽"))   # 九三 上，六二 承之
        self.assertEqual(by_pos[1], "")                     # 初爻無下鄰

    def test_dong_summary_names_the_moving_line(self):
        for dong in range(1, 7):
            with self.subTest(dong=dong):
                board = analyze_yao_positions("110101", dong)
                expected = board["六爻"][dong - 1]["名稱"]
                self.assertTrue(board["動爻摘要"].startswith(f"{expected}（動）："),
                                board["動爻摘要"])

    def test_board_emitted_on_every_cast(self):
        for result in (qigua_by_numbers(6, 8), qigua_by_time(2024, 1, 15, 10)):
            self.assertIn("爻位盤", result)
            self.assertEqual(len(result["爻位盤"]["六爻"]), 6)
            self.assertEqual(result["本卦"]["動爻位"],
                             int(result["本卦"]["動爻"].replace("第", "").replace("爻", "")))

    def test_moving_line_yinyang_matches_binary_and_board(self):
        """本卦【動爻陰陽】必須同時對得上二進位（初爻為最右位元）與爻位盤那一列"""
        for u in range(1, 9):
            for dong in range(1, 7):
                with self.subTest(upper=u, dong=dong):
                    result = _analyze_hexagram(u, 8, dong)
                    binary = result["本卦"]["二進位"]
                    expected = "陽" if binary[6 - dong] == "1" else "陰"
                    self.assertEqual(result["本卦"]["動爻陰陽"], expected)
                    self.assertEqual(result["爻位盤"]["六爻"][dong - 1]["陰陽"], expected)


# ============================================================================
# 4a-5. 卦德（《說卦傳》）
# ============================================================================
class TestGuaDe(unittest.TestCase):

    def test_every_trigram_has_a_de_with_an_intent(self):
        self.assertEqual(len(BAGUA), 8)
        des = {info["de"] for info in BAGUA.values()}
        self.assertEqual(len(des), 8, f"八卦卦德應互異，實得 {des}")
        self.assertEqual(des, set(GUADE_INTENT), "卦德與意向表不同步")

    def test_shuogua_assignments(self):
        """《說卦傳》：乾健、坤順、震動、巽入、坎陷、離麗、艮止、兌說"""
        expected = {1: "健", 2: "說", 3: "麗", 4: "動",
                    5: "入", 6: "陷", 7: "止", 8: "順"}
        for num, de in expected.items():
            self.assertEqual(BAGUA[num]["de"], de, f"{BAGUA[num]['name']} 卦德應為 {de}")

    def test_same_de_reports_alignment(self):
        self.assertIn("同德相應", analyze_guade(1, 1))

    def test_polar_pairs_get_specific_note(self):
        for a, b in [(1, 8), (4, 7), (6, 3), (2, 5)]:   # 健順 動止 陷麗 說入
            with self.subTest(pair=(BAGUA[a]["name"], BAGUA[b]["name"])):
                text = analyze_guade(a, b)
                self.assertNotIn("兩股力性質不同", text,
                                 "傳統對舉的兩極應有專屬說法，不應落入泛用句")

    def test_guade_is_symmetric_in_note_but_not_in_subject(self):
        """卦德關係描述體與用各自的取向，故 A遇B 與 B遇A 不同句"""
        self.assertNotEqual(analyze_guade(1, 8), analyze_guade(8, 1))


# ============================================================================
# 4b. 乾為天 / 坤為地 互卦取自變卦
# ============================================================================
class TestPureGuaHuFromBian(unittest.TestCase):
    """六爻皆同者，互卦每一段都得本卦自身，等於沒有取象；
    原書規定乾為天、坤為地改從變卦取互。"""

    def test_qian_hu_from_bian(self):
        """乾為天動初爻 → 變天風姤(111110)，互取自變卦 = 乾為天(111111)"""
        result = _analyze_hexagram(1, 1, 1)
        self.assertEqual(result["本卦"]["名稱"], "乾為天")
        self.assertTrue(result["互卦"]["取自變卦"])
        self.assertEqual(result["變卦"]["名稱"], "天風姤")
        self.assertEqual(result["互卦"]["名稱"], "乾為天")

    def test_kun_hu_from_bian(self):
        """坤為地動三爻 → 變地山謙(000100)，互取自變卦 = 雷水解"""
        result = _analyze_hexagram(8, 8, 3)
        self.assertEqual(result["本卦"]["名稱"], "坤為地")
        self.assertTrue(result["互卦"]["取自變卦"])
        self.assertEqual(result["互卦"]["名稱"], "雷水解")

    def test_ordinary_gua_hu_from_ben(self):
        """一般卦互卦仍取自本卦，不得誤觸此規則"""
        result = _analyze_hexagram(6, 8, 2)  # 水地比
        self.assertFalse(result["互卦"]["取自變卦"])
        self.assertEqual(result["互卦"]["名稱"], "山地剝")


# ============================================================================
# 4c. 日始於子時：23 時推次日
# ============================================================================
class TestZishiDayRoll(unittest.TestCase):
    """原書「日始於子時」：23:00–23:59 已入次日子時，日數取次日。"""

    def test_23_hour_rolls_to_next_day(self):
        """農曆 2024/6/15 23時 應與 2024/6/16 23時之前的日數一致"""
        rolled = qigua_by_time(2024, 6, 15, 23)
        self.assertEqual(rolled["計算過程"]["日數"], 16)
        self.assertIn("子時推日", rolled["計算過程"])

    def test_22_hour_does_not_roll(self):
        """22 時屬亥時，仍為當日"""
        result = qigua_by_time(2024, 6, 15, 22)
        self.assertEqual(result["計算過程"]["日數"], 15)
        self.assertNotIn("子時推日", result["計算過程"])

    def test_month_end_rolls_into_next_month(self):
        """月末 23 時應進入次月初一，而非產生第 30/31 日"""
        info = YEAR_INFOS[2024 - 1900]
        last = _month_days(info, 6, False)
        result = qigua_by_time(2024, 6, last, 23)
        self.assertEqual(result["計算過程"]["日數"], 1)
        self.assertEqual(result["計算過程"]["月數"], 7)

    def test_year_end_rolls_into_next_year(self):
        """臘月月末 23 時應進入次年正月初一，年地支同步進位"""
        info = YEAR_INFOS[2024 - 1900]
        last = _month_days(info, 12, False)
        result = qigua_by_time(2024, 12, last, 23)
        self.assertEqual(result["計算過程"]["月數"], 1)
        self.assertEqual(result["計算過程"]["日數"], 1)
        self.assertIn(DIZHI[get_year_dizhi(2025)[0]], result["計算過程"]["年數"])

    def test_gregorian_entry_rolls_once_only(self):
        """西曆入口只透過 qigua_by_time 推日一次，不得重複推日"""
        gz = qigua_by_gregorian_time(2024, 7, 20, 23)   # 農曆 2024/6/15
        ln = qigua_by_time(2024, 6, 15, 23)
        self.assertEqual(gz["本卦"]["序號"], ln["本卦"]["序號"])
        self.assertEqual(gz["本卦"]["動爻"], ln["本卦"]["動爻"])
        # 日期轉換顯示的是實際起卦所用的農曆日（已推日）
        self.assertIn("6月16日", gz["日期轉換"]["農曆"])
        self.assertIn("日始於子時", gz["日期轉換"]["說明"])


# ============================================================================
# 4d. 農曆日加一天（含閏月轉入）
# ============================================================================
class TestLunarNextDay(unittest.TestCase):

    def test_mid_month(self):
        self.assertEqual(lunar_next_day(2024, 6, 15), (2024, 6, 16, False))

    def test_into_leap_month(self):
        """2023 閏二月：二月月末的次日應為閏二月初一"""
        info = YEAR_INFOS[2023 - 1900]
        self.assertEqual(info & 0xF, 2, "2023 應為閏二月")
        last = _month_days(info, 2, False)
        self.assertEqual(lunar_next_day(2023, 2, last), (2023, 2, 1, True))

    def test_out_of_leap_month(self):
        """閏二月月末的次日應為三月初一"""
        info = YEAR_INFOS[2023 - 1900]
        last = _month_days(info, 2, True)
        self.assertEqual(lunar_next_day(2023, 2, last, True), (2023, 3, 1, False))


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
# 5b. 分秒精度起卦（今人擴充，非邵雍原法）
# ============================================================================
class TestPreciseCasting(unittest.TestCase):
    """純時辰起卦在同一時辰（2 小時）內恆得同卦；分入下卦、秒入動爻可分辨。"""

    def test_minute_changes_lower_gua_or_dong(self):
        a = qigua_by_time_precise(2024, 1, 15, 10, 0, 0)
        b = qigua_by_time_precise(2024, 1, 15, 10, 30, 0)
        self.assertNotEqual(
            (a["本卦"]["二進位"], a["本卦"]["動爻"]),
            (b["本卦"]["二進位"], b["本卦"]["動爻"]),
            "同時辰不同分鐘應得不同卦")

    def test_second_changes_dong_yao(self):
        a = qigua_by_time_precise(2024, 1, 15, 10, 0, 0)
        b = qigua_by_time_precise(2024, 1, 15, 10, 0, 1)
        self.assertEqual(a["本卦"]["二進位"], b["本卦"]["二進位"], "秒只入動爻")
        self.assertNotEqual(a["本卦"]["動爻"], b["本卦"]["動爻"])

    def test_upper_gua_unaffected_by_minute_and_second(self):
        base = qigua_by_time_precise(2024, 1, 15, 10, 0, 0)["本卦"]["上卦"]
        for minute, second in [(7, 0), (0, 41), (59, 59)]:
            with self.subTest(minute=minute, second=second):
                got = qigua_by_time_precise(2024, 1, 15, 10, minute, second)
                self.assertEqual(got["本卦"]["上卦"], base, "上卦只由年月日時辰決定")

    def test_shichen_precision_is_constant_within_the_hour_pair(self):
        """對照組：傳統時辰起卦在同一時辰內確實恆同——這正是精度擴充要解決的事"""
        a = qigua_by_time(2024, 1, 15, 9)
        b = qigua_by_time(2024, 1, 15, 10)
        self.assertEqual(a["本卦"]["二進位"], b["本卦"]["二進位"])

    def test_precise_applies_zishi_and_season(self):
        rolled = qigua_by_time_precise(2024, 6, 15, 23, 30, 30)
        self.assertEqual(rolled["計算過程"]["日數"], 16)
        self.assertIn("子時推日", rolled["計算過程"])
        self.assertIn("卦氣旺衰", rolled)

    def test_gregorian_precise_matches_lunar_precise(self):
        gz = qigua_by_gregorian_time_precise(2024, 2, 10, 11, 22, 33)
        ln = qigua_by_time_precise(2024, 1, 1, 11, 22, 33)
        self.assertEqual(gz["本卦"]["序號"], ln["本卦"]["序號"])
        self.assertEqual(gz["本卦"]["動爻"], ln["本卦"]["動爻"])
        self.assertIn("11:22:33", gz["日期轉換"]["西曆"])


# ============================================================================
# 5c. 數字起卦 + 占時（日期只定時令，不入起卦之數）
# ============================================================================
class TestNumbersAt(unittest.TestCase):

    def test_date_does_not_change_the_hexagram(self):
        plain = qigua_by_numbers(6, 8, 3)
        for gy, gm, gd in [(2024, 1, 15), (2024, 7, 20), (2025, 11, 2)]:
            with self.subTest(date=(gy, gm, gd)):
                at = qigua_by_numbers_at(gy, gm, gd, 10, 6, 8, 3)
                self.assertEqual(at["本卦"]["二進位"], plain["本卦"]["二進位"])
                self.assertEqual(at["本卦"]["動爻"], plain["本卦"]["動爻"])

    def test_date_supplies_the_season(self):
        spring = qigua_by_numbers_at(2024, 2, 20, 10, 6, 8)   # 農曆正月 → 春
        self.assertIn("卦氣旺衰", spring)
        self.assertIn("春", spring["卦氣旺衰"]["時令"])
        self.assertIn("占時", spring["計算過程"])
        self.assertNotIn("卦氣旺衰", qigua_by_numbers(6, 8))

    def test_zishi_agrees_with_time_casting(self):
        """23 時的數字占與同刻的時間占必須落在同一時令，不可兩處說法不同"""
        at = qigua_by_numbers_at(2024, 7, 20, 23, 6, 8)      # 農曆 6/15 → 推 6/16
        timed = qigua_by_gregorian_time(2024, 7, 20, 23)
        self.assertEqual(at["卦氣旺衰"]["時令"], timed["卦氣旺衰"]["時令"])
        self.assertIn("次日", at["計算過程"]["占時"])


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

    # 路徑步驟：「→ 目標（變N爻[得R%]）」。多段路徑（大過 → 夬 → 革）逐段都有
    # 自己的變爻，故單段與多段共用同一組解析規則，不再有無法驗證的漏網條目。
    STEP_RE = r"→\s*([^（(→]+?)\s*（變(\d)爻(?:得(\d+)%)?）"

    @classmethod
    def parse_path(cls, path: str):
        """回傳 [(目標卦名, 變爻, 吉率或 None), ...]；無法解析則回傳 []"""
        import re
        return [(m.group(1).strip(), int(m.group(2)),
                 int(m.group(3)) if m.group(3) else None)
                for m in re.finditer(cls.STEP_RE, path)]

    def test_change_paths_use_bottom_up_yao(self):
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
            steps = self.parse_path(path)
            self.assertTrue(steps, f"卦{num} 的變卦路徑無法解析，等同無人驗證：{path!r}")
            # 逐段套用變爻，每一段的結果都必須等於該段宣稱的卦
            binary = num_to_bin[num]
            for tgt_name, yao, _pct in steps:
                self.assertIn(tgt_name, name_to_num,
                              f"卦{num}：無法解析目標卦名 {tgt_name!r} ← {path!r}")
                binary = apply_change(binary, yao)
                got = HEXAGRAMS[binary_to_gua_pair(binary)][0]
                self.assertEqual(
                    got, name_to_num[tgt_name],
                    f"卦{num} {self.SHORT[num]}：變{yao}爻得 {self.SHORT.get(got)}({got})，"
                    f"但路徑宣稱變為 {tgt_name}({name_to_num[tgt_name]})：{path!r}")
            checked += 1
        self.assertEqual(checked, 40,
                         f"變卦路徑應 40 條且全數可驗證，實得 {checked}")


# ============================================================================
# 8. 策略表 markdown ↔ 程式碼同步（F2 回歸測試）
# ============================================================================
class TestStrategyMarkdownSync(unittest.TestCase):
    """references/hexagram-strategy.md 必須與 meihua_calc.HEXAGRAM_STRATEGY 完全
    同步（CLAUDE.md 列為關鍵不變式）：64 列速查表的吉率/類型/策略/卦名一致，
    每條變卦路徑的目標/變爻/吉率一致，且路徑「得R%」等於目標卦自身的吉率。
    此測試防止程式碼與 markdown 之一被單方面修改而產生矛盾讀數。"""

    MD_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "references", "hexagram-strategy.md")

    def _read_md(self) -> str:
        with open(self.MD_PATH, encoding="utf-8") as fh:
            return fh.read()

    def test_main_table_in_sync(self):
        import re

        from meihua_calc import HEXAGRAM_STRATEGY

        short = TestStrategyChangePaths.SHORT
        rows = {}
        for m in re.finditer(r"^(\d+)\|(.+?)\|(\d+)%\|(.+?)\|(.+?)\s*$",
                             self._read_md(), re.M):
            rows[int(m.group(1))] = (m.group(2).strip(), int(m.group(3)),
                                     m.group(4).strip(), m.group(5).strip())
        self.assertEqual(len(rows), 64, f"速查表應 64 列，實得 {len(rows)}")
        for num, (typ, adv, jr, _path) in HEXAGRAM_STRATEGY.items():
            self.assertIn(num, rows, f"卦{num} 缺於 markdown 速查表")
            md_name, md_jr, md_typ, md_adv = rows[num]
            self.assertEqual(
                (md_name, md_jr, md_typ, md_adv), (short[num], jr, typ, adv),
                f"卦{num} 速查表不同步：md={rows[num]} "
                f"code={(short[num], jr, typ, adv)}")

    def test_change_paths_in_sync(self):
        import re

        from meihua_calc import HEXAGRAM_STRATEGY

        short = TestStrategyChangePaths.SHORT
        name_to_num = {v: k for k, v in short.items()}

        code = {}
        for num, (_typ, _adv, _jr, path) in HEXAGRAM_STRATEGY.items():
            if not path:
                continue
            steps = TestStrategyChangePaths.parse_path(path)
            self.assertTrue(steps, f"卦{num} 路徑無法解析：{path!r}")
            code[num] = tuple(steps)

        # markdown 側用半形括號、且中繼段不帶 %：2坤→謙(變3爻83%) /
        # 28大過→夬(變1爻)→革(變2爻50%)
        md = {}
        for entry in re.finditer(
                r"(\d+)([^\d,，()（）→\s]+)((?:→[^\d,，()（）→\s]+\(變\d爻(?:\d+%)?\))+)",
                self._read_md()):
            steps = [(m.group(1), int(m.group(2)),
                      int(m.group(3)) if m.group(3) else None)
                     for m in re.finditer(
                         r"→([^\d,，()（）→\s]+)\(變(\d)爻(?:(\d+)%)?\)",
                         entry.group(3))]
            md[int(entry.group(1))] = tuple(steps)

        self.assertEqual(
            set(code), set(md),
            f"變卦路徑來源卦不一致：code−md={set(code) - set(md)} "
            f"md−code={set(md) - set(code)}")
        for num in code:
            self.assertEqual(
                code[num], md[num],
                f"卦{num} {short[num]} 路徑不同步：code={code[num]} md={md[num]}")
            # 路徑末段的「得R%」必須等於目標卦自身的吉率
            tgt_name, _yao, pct = code[num][-1]
            self.assertIsNotNone(pct, f"卦{num} 路徑末段應標示吉率：{code[num]}")
            tgt_num = name_to_num[tgt_name]
            self.assertEqual(
                pct, HEXAGRAM_STRATEGY[tgt_num][2],
                f"卦{num} 路徑得{pct}% 但目標 {tgt_name} "
                f"吉率={HEXAGRAM_STRATEGY[tgt_num][2]}%")


if __name__ == "__main__":
    unittest.main(verbosity=2)
