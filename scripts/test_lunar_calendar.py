#!/usr/bin/env python3
"""
Tier 5：農曆轉換單元測試

驗證項目：
  1. YEAR_INFOS 資料表完整性（1900-2099 共 200 年）
  2. 起點對齊：1900-01-31 = 農曆 1900/1/1
  3. 已知春節對照（2020, 2023, 2024, 2025, 2026 多年驗證）
  4. 已知傳統節日（端午 5/5、中秋 8/15）
  5. 閏月處理（2023 閏二月、2020 閏四月、2014 閏九月、2017 閏六月）
  6. 跨年邊界：西曆 1 月初仍屬農曆上一年
  7. 連續日期應產生連續農曆日期（一致性測試 - 隨機抽樣）
  8. 邊界錯誤：1899、2100 應拋 ValueError
  9. 年地支：1900 庚子、1984 甲子、2024 甲辰、2026 丙午
 10. 時辰映射：子時涵蓋 23 + 0 兩個小時

農曆資料表錯一格 → 跨日 → 起卦時辰整個錯。
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from meihua_calc import (  # noqa: E402
    YEAR_INFOS,
    get_shichen,
    get_year_dizhi,
    gregorian_to_lunar,
)


# ============================================================================
# 1. YEAR_INFOS 完整性
# ============================================================================
class TestYearInfosTable(unittest.TestCase):

    def test_200_years_coverage(self):
        """應涵蓋 1900-2099 共 200 年"""
        self.assertEqual(len(YEAR_INFOS), 200)

    def test_all_positive_integers(self):
        for i, info in enumerate(YEAR_INFOS):
            self.assertIsInstance(info, int, f"{1900+i} 年資料應為整數")
            self.assertGreater(info, 0, f"{1900+i} 年資料應為正數")

    def test_leap_month_field_in_range(self):
        """bits 0-3 (閏月月份) 必在 0-12 範圍"""
        for i, info in enumerate(YEAR_INFOS):
            leap = info & 0xF
            self.assertIn(leap, range(0, 13),
                          f"{1900+i} 年閏月欄位 {leap} 超出範圍")


# ============================================================================
# 2. 起點對齊
# ============================================================================
class TestLunarStartDate(unittest.TestCase):
    """1900-01-31 為農曆 1900/1/1（資料表錨點）"""

    def test_anchor_date(self):
        self.assertEqual(gregorian_to_lunar(1900, 1, 31), (1900, 1, 1, False))

    def test_day_after_anchor(self):
        self.assertEqual(gregorian_to_lunar(1900, 2, 1), (1900, 1, 2, False))

    def test_day_before_anchor_raises(self):
        with self.assertRaises(ValueError):
            gregorian_to_lunar(1900, 1, 30)


# ============================================================================
# 3. 已知春節對照
# ============================================================================
class TestKnownSpringFestivals(unittest.TestCase):
    """各年農曆正月初一 = 該年春節（國際公認日期）"""

    SPRING_FESTIVALS = [
        # (西曆年, 西曆月, 西曆日, 農曆年)
        (1900, 1, 31, 1900),
        (2000, 2, 5,  2000),  # 庚辰年春節
        (2020, 1, 25, 2020),  # 庚子年春節
        (2023, 1, 22, 2023),  # 癸卯年春節
        (2024, 2, 10, 2024),  # 甲辰年春節
        (2025, 1, 29, 2025),  # 乙巳年春節
        (2026, 2, 17, 2026),  # 丙午年春節
    ]

    def test_all_spring_festivals(self):
        for y, m, d, lunar_y in self.SPRING_FESTIVALS:
            with self.subTest(date=f"{y}-{m:02d}-{d:02d}"):
                result = gregorian_to_lunar(y, m, d)
                self.assertEqual(
                    result, (lunar_y, 1, 1, False),
                    f"{y}-{m:02d}-{d:02d} 應為農曆 {lunar_y}/1/1，實得 {result}"
                )


# ============================================================================
# 4. 傳統節日（端午 5/5、中秋 8/15）
# ============================================================================
class TestTraditionalFestivals(unittest.TestCase):

    # (西曆年, 西曆月, 西曆日, 期望農曆 tuple)
    DUANWU = [
        (2023, 6, 22, (2023, 5, 5, False)),
        (2024, 6, 10, (2024, 5, 5, False)),
    ]
    ZHONGQIU = [
        (2023, 9, 29, (2023, 8, 15, False)),
        (2024, 9, 17, (2024, 8, 15, False)),
    ]

    def test_duanwu_festivals(self):
        for y, m, d, expected in self.DUANWU:
            with self.subTest(date=f"{y}-{m:02d}-{d:02d}"):
                self.assertEqual(gregorian_to_lunar(y, m, d), expected)

    def test_zhongqiu_festivals(self):
        for y, m, d, expected in self.ZHONGQIU:
            with self.subTest(date=f"{y}-{m:02d}-{d:02d}"):
                self.assertEqual(gregorian_to_lunar(y, m, d), expected)


# ============================================================================
# 5. 閏月處理
# ============================================================================
class TestLeapMonths(unittest.TestCase):
    """各年閏月初一日期對照"""

    LEAP_FIRST_DAYS = [
        # (西曆年, 西曆月, 西曆日, 期望農曆閏月 (year, month, day, is_leap=True))
        (2023, 3, 22, (2023, 2, 1, True)),   # 2023 閏二月
        (2020, 5, 23, (2020, 4, 1, True)),   # 2020 閏四月
        (2017, 7, 23, (2017, 6, 1, True)),   # 2017 閏六月
        (2014, 10, 24, (2014, 9, 1, True)),  # 2014 閏九月
    ]

    def test_leap_month_first_days(self):
        for y, m, d, expected in self.LEAP_FIRST_DAYS:
            with self.subTest(date=f"{y}-{m:02d}-{d:02d}"):
                self.assertEqual(gregorian_to_lunar(y, m, d), expected)

    def test_2023_leap_feb_distinct_from_normal_feb(self):
        """2023 年正二月 vs 閏二月必須區分"""
        # 2023 正二月初一 = 2023-02-20
        normal = gregorian_to_lunar(2023, 2, 20)
        self.assertEqual(normal, (2023, 2, 1, False))
        # 2023 閏二月初一 = 2023-03-22
        leap = gregorian_to_lunar(2023, 3, 22)
        self.assertEqual(leap, (2023, 2, 1, True))
        self.assertNotEqual(normal, leap)


# ============================================================================
# 6. 跨年邊界
# ============================================================================
class TestCrossYearBoundary(unittest.TestCase):
    """西曆 1 月份在某些年仍屬農曆上一年"""

    def test_2024_jan_1_is_lunar_2023(self):
        """西曆 2024-01-01 在農曆 2024 年春節前 → 屬農曆 2023 年"""
        lunar_year, _, _, _ = gregorian_to_lunar(2024, 1, 1)
        self.assertEqual(lunar_year, 2023, "2024-01-01 應屬農曆 2023 年")

    def test_day_before_chunjie_2024(self):
        """2024 春節 2024-02-10 的前一天應為農曆 2023 年最後一天"""
        eve = gregorian_to_lunar(2024, 2, 9)
        self.assertEqual(eve[0], 2023)
        self.assertEqual(eve[1], 12)
        # 12 月應為最後一日（29 或 30，視該月大小）
        self.assertIn(eve[2], (29, 30))

    def test_year_transition_at_chunjie(self):
        """春節當日 → 隔日：年/月/日應正確跨入新年"""
        before = gregorian_to_lunar(2024, 2, 9)   # 除夕（2023 年最後一天）
        after = gregorian_to_lunar(2024, 2, 10)   # 春節（2024 年初一）
        self.assertEqual(after, (2024, 1, 1, False))
        self.assertEqual(before[0], 2023)


# ============================================================================
# 7. 連續性測試（隨機抽樣，相鄰兩日農曆值應遞增 1）
# ============================================================================
class TestContinuity(unittest.TestCase):
    """連續西曆日期 → 農曆應連續遞增（不跳日）"""

    def test_30_consecutive_days_in_2024(self):
        prev = None
        d = date(2024, 6, 1)
        for _ in range(30):
            curr = gregorian_to_lunar(d.year, d.month, d.day)
            if prev is not None:
                # 簡化檢查：日數要嘛 +1，要嘛換月時重新從 1 開始
                if curr[1] == prev[1] and curr[3] == prev[3]:
                    self.assertEqual(curr[2], prev[2] + 1,
                                     f"{d}：農曆日跳號 {prev} → {curr}")
                else:
                    # 跨月（含進入閏月）
                    self.assertEqual(curr[2], 1, f"{d}：跨月時日應為 1")
            prev = curr
            d += timedelta(days=1)

    def test_continuity_across_leap_2023(self):
        """2023 閏二月邊界：正二月結束 → 閏二月初一"""
        # 正二月最後一日（29 或 30）→ 閏二月初一
        # 用 reverse：找到 normal 2 月結束的西曆日，下一天必為閏 2/1
        d = date(2023, 3, 20)
        results = []
        for _ in range(5):
            results.append((d, gregorian_to_lunar(d.year, d.month, d.day)))
            d += timedelta(days=1)
        # 預期 2023-03-22 = 閏 2/1
        leap_first = next(r for r in results if r[1] == (2023, 2, 1, True))
        self.assertEqual(leap_first[0], date(2023, 3, 22))


# ============================================================================
# 8. 邊界錯誤
# ============================================================================
class TestBoundaryErrors(unittest.TestCase):

    def test_year_too_early(self):
        with self.assertRaises(ValueError):
            gregorian_to_lunar(1899, 12, 31)

    def test_year_too_late(self):
        with self.assertRaises(ValueError):
            gregorian_to_lunar(2100, 1, 1)


# ============================================================================
# 9. 年地支
# ============================================================================
class TestYearDizhi(unittest.TestCase):
    """農曆年 → 地支序號與名稱"""

    EXPECTED = [
        (1900, 1, "子"),   # 庚子
        (1924, 1, "子"),   # 甲子（六十甲子起點）
        (1984, 1, "子"),   # 甲子
        (2012, 5, "辰"),   # 壬辰
        (2024, 5, "辰"),   # 甲辰
        (2025, 6, "巳"),   # 乙巳
        (2026, 7, "午"),   # 丙午
        (2099, 8, "未"),   # 己未
    ]

    def test_all_year_dizhi(self):
        for lunar_year, expected_num, expected_name in self.EXPECTED:
            with self.subTest(year=lunar_year):
                num, name = get_year_dizhi(lunar_year)
                self.assertEqual(num, expected_num,
                                 f"{lunar_year} 年地支序號")
                self.assertEqual(name, expected_name,
                                 f"{lunar_year} 年地支名")

    def test_dizhi_cycles_every_12_years(self):
        for y in range(1900, 2080):
            self.assertEqual(get_year_dizhi(y), get_year_dizhi(y + 12))


# ============================================================================
# 10. 時辰映射
# ============================================================================
class TestShichen(unittest.TestCase):
    """24 小時 → 12 時辰（子時跨 23 + 0 兩小時）"""

    # (hour, expected_num, expected_name)
    EXPECTED = [
        (0,  1, "子"),    # 子時前段
        (23, 1, "子"),    # 子時後段
        (1,  2, "丑"),
        (2,  2, "丑"),
        (3,  3, "寅"),
        (5,  4, "卯"),
        (7,  5, "辰"),
        (9,  6, "巳"),
        (11, 7, "午"),
        (12, 7, "午"),
        (13, 8, "未"),
        (15, 9, "申"),
        (17, 10, "酉"),
        (19, 11, "戌"),
        (21, 12, "亥"),
    ]

    def test_known_shichen_values(self):
        for hour, exp_num, exp_name in self.EXPECTED:
            with self.subTest(hour=hour):
                num, name = get_shichen(hour)
                self.assertEqual(num, exp_num, f"{hour} 時辰序號")
                self.assertEqual(name, exp_name, f"{hour} 時辰名")

    def test_24_hours_all_covered(self):
        """0-23 每個小時都應有對應時辰"""
        for h in range(24):
            num, name = get_shichen(h)
            self.assertIn(num, range(1, 13))
            self.assertEqual(len(name), 1)

    def test_zi_shi_spans_two_hours(self):
        """子時在 23 點與 0 點都應對應"""
        self.assertEqual(get_shichen(23)[1], "子")
        self.assertEqual(get_shichen(0)[1], "子")

    def test_each_shichen_covers_two_hours(self):
        """每個時辰應對應 2 個小時"""
        counts = {}
        for h in range(24):
            name = get_shichen(h)[1]
            counts[name] = counts.get(name, 0) + 1
        for name, count in counts.items():
            self.assertEqual(count, 2, f"時辰 {name} 應對應 2 小時，實得 {count}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
