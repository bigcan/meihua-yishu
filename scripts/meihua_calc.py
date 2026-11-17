#!/usr/bin/env python3
"""
梅花易數起卦計算工具
Meihua Yishu (Plum Blossom Numerology) Calculator

內建農曆轉換功能，無需外部依賴。
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import Tuple, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calendar_util as cal  # noqa: E402  節氣月建（卦氣旺衰依月建，不依農曆月）


def configure_stdout() -> None:
    """CLI 輸出含中文與符號（📿⚠️）。Windows 主控台預設 cp950/cp437，遇到無法
    編碼的字元會直接拋 UnicodeEncodeError，整份起卦結果就此中斷——寧可個別字元
    顯示為 ?，也不要讓使用者拿不到卦。

    三個 CLI 入口（meihua_calc / jinqian_gua / najia）都在 __main__ 開頭呼叫。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:  # 被重導向到非 TextIOWrapper 時沒有這個方法
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError, AttributeError):
            try:
                reconfigure(errors="replace")
            except (ValueError, OSError, AttributeError):
                pass

# 農曆數據表 (1900-2099)
# 編碼格式：
# - bit 16: 閏月是否為大月（30天=1，29天=0）
# - bits 4-15: 各月是否為大月（倒序：bit 15=1月，bit 4=12月）
# - bits 0-3: 閏月月份（0表示無閏月，1-12表示閏幾月）
# 數據來源：中國天文台農曆曆譜
YEAR_INFOS = [
    # 1900-1909
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,
    # 1910-1919
    0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,
    # 1920-1929
    0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,
    # 1930-1939
    0x06566, 0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,
    # 1940-1949
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,
    # 1950-1959
    0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5d0, 0x14573, 0x052d0, 0x0a9a8, 0x0e950, 0x06aa0,
    # 1960-1969
    0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,
    # 1970-1979
    0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b5a0, 0x195a6,
    # 1980-1989
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,
    # 1990-1999
    0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x05ac0, 0x0ab60, 0x096d5, 0x092e0,
    # 2000-2009
    0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,
    # 2010-2019
    0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,
    # 2020-2029
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,
    # 2030-2039
    0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,
    # 2040-2049
    0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,
    # 2050-2059
    0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06aa0, 0x1a6c4, 0x0aae0,
    # 2060-2069
    0x092e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,
    # 2070-2079
    0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,
    # 2080-2089
    0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,
    # 2090-2099
    0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252,
]

# 農曆1900年正月初一對應的西曆日期
LUNAR_START_DATE = date(1900, 1, 31)

# 先天八卦數對應
BAGUA = {
    1: {"name": "乾", "symbol": "☰", "binary": "111", "element": "金", "family": "父",   "de": "健"},
    2: {"name": "兌", "symbol": "☱", "binary": "011", "element": "金", "family": "少女", "de": "說"},
    3: {"name": "離", "symbol": "☲", "binary": "101", "element": "火", "family": "中女", "de": "麗"},
    4: {"name": "震", "symbol": "☳", "binary": "001", "element": "木", "family": "長男", "de": "動"},
    5: {"name": "巽", "symbol": "☴", "binary": "110", "element": "木", "family": "長女", "de": "入"},
    6: {"name": "坎", "symbol": "☵", "binary": "010", "element": "水", "family": "中男", "de": "陷"},
    7: {"name": "艮", "symbol": "☶", "binary": "100", "element": "土", "family": "少男", "de": "止"},
    8: {"name": "坤", "symbol": "☷", "binary": "000", "element": "土", "family": "母",   "de": "順"},
}

# 卦德（《說卦傳》「乾健也，坤順也，震動也……」）：八卦的性情取向。
# 相對於五行生剋的「強弱判決」，卦德給的是「象的關係」——兩者互補，皆為透鏡非判決。
GUADE_INTENT = {
    "健": "剛健主導、進取不息",
    "說": "和悅交流、取悅外應",
    "麗": "附麗顯明、依託而光",
    "動": "起而行動、振奮求變",
    "入": "漸進順入、謙伏滲透",
    "陷": "涉險應變、勞心趨流",
    "止": "靜止守成、止於其所",
    "順": "柔順承載、包容隨順",
}

# 四組傳統對舉的卦德兩極；不在表中者僅作「性質不同」處理，不強行編派吉凶。
_GUADE_POLAR = {
    frozenset({"健", "順"}): "一剛一柔：主導與承載之間，看你要推進還是承接",
    frozenset({"動", "止"}): "一動一靜：進與守的拉扯，急動或久守都不易",
    frozenset({"陷", "麗"}): "一陷一明：身處險而前方有明，關鍵在能否脫險見光",
    frozenset({"說", "入"}): "一悅一巽：外和而內順，宜柔不宜剛",
}

# 六十四卦名稱
HEXAGRAMS = {
    (1, 1): (1, "乾為天"),    (1, 2): (10, "天澤履"),   (1, 3): (13, "天火同人"), (1, 4): (25, "天雷无妄"),
    (1, 5): (44, "天風姤"),   (1, 6): (6, "天水訟"),    (1, 7): (33, "天山遯"),   (1, 8): (12, "天地否"),
    (2, 1): (43, "澤天夬"),   (2, 2): (58, "兌為澤"),   (2, 3): (49, "澤火革"),   (2, 4): (17, "澤雷隨"),
    (2, 5): (28, "澤風大過"), (2, 6): (47, "澤水困"),   (2, 7): (31, "澤山咸"),   (2, 8): (45, "澤地萃"),
    (3, 1): (14, "火天大有"), (3, 2): (38, "火澤睽"),   (3, 3): (30, "離為火"),   (3, 4): (21, "火雷噬嗑"),
    (3, 5): (50, "火風鼎"),   (3, 6): (64, "火水未濟"), (3, 7): (56, "火山旅"),   (3, 8): (35, "火地晉"),
    (4, 1): (34, "雷天大壯"), (4, 2): (54, "雷澤歸妹"), (4, 3): (55, "雷火豐"),   (4, 4): (51, "震為雷"),
    (4, 5): (32, "雷風恆"),   (4, 6): (40, "雷水解"),   (4, 7): (62, "雷山小過"), (4, 8): (16, "雷地豫"),
    (5, 1): (9, "風天小畜"),  (5, 2): (61, "風澤中孚"), (5, 3): (37, "風火家人"), (5, 4): (42, "風雷益"),
    (5, 5): (57, "巽為風"),   (5, 6): (59, "風水渙"),   (5, 7): (53, "風山漸"),   (5, 8): (20, "風地觀"),
    (6, 1): (5, "水天需"),    (6, 2): (60, "水澤節"),   (6, 3): (63, "水火既濟"), (6, 4): (3, "水雷屯"),
    (6, 5): (48, "水風井"),   (6, 6): (29, "坎為水"),   (6, 7): (39, "水山蹇"),   (6, 8): (8, "水地比"),
    (7, 1): (26, "山天大畜"), (7, 2): (41, "山澤損"),   (7, 3): (22, "山火賁"),   (7, 4): (27, "山雷頤"),
    (7, 5): (18, "山風蠱"),   (7, 6): (4, "山水蒙"),    (7, 7): (52, "艮為山"),   (7, 8): (23, "山地剝"),
    (8, 1): (11, "地天泰"),   (8, 2): (19, "地澤臨"),   (8, 3): (36, "地火明夷"), (8, 4): (24, "地雷復"),
    (8, 5): (46, "地風升"),   (8, 6): (7, "地水師"),    (8, 7): (15, "地山謙"),   (8, 8): (2, "坤為地"),
}

# 時辰對照（子時為23:00-00:59）
SHICHEN = {
    0: (1, "子"), 1: (2, "丑"), 2: (2, "丑"), 3: (3, "寅"), 4: (3, "寅"), 5: (4, "卯"),
    6: (4, "卯"), 7: (5, "辰"), 8: (5, "辰"), 9: (6, "巳"), 10: (6, "巳"), 11: (7, "午"),
    12: (7, "午"), 13: (8, "未"), 14: (8, "未"), 15: (9, "申"), 16: (9, "申"), 17: (10, "酉"),
    18: (10, "酉"), 19: (11, "戌"), 20: (11, "戌"), 21: (12, "亥"), 22: (12, "亥"), 23: (1, "子"),
}

# 二進位 → 卦數 反查表
BINARY_TO_GUA = {info["binary"]: num for num, info in BAGUA.items()}


def _year_days(year_info: int) -> int:
    """計算農曆年的總天數"""
    # 基礎天數: 12個月 × 29天
    days = 29 * 12
    # 如果有閏月，加29天
    leap_month = year_info & 0xF
    if leap_month:
        days += 29
        # 閏月是否為大月由 bit 16 決定
        if (year_info >> 16) & 1:
            days += 1
    # 檢查 12 個正常月份是否為大月（30天）
    # bits 4-15 對應月份 12-1（倒序）
    for month in range(1, 13):
        if (year_info >> (16 - month)) & 1:
            days += 1
    return days


def _month_days(year_info: int, month: int, is_leap: bool = False) -> int:
    """計算農曆某月的天數"""
    if is_leap:
        # 閏月天數由 bit 16 決定
        return 30 if (year_info >> 16) & 1 else 29

    # 正常月份天數由 bits 4-15 決定（月份1對應bit 15，月份12對應bit 4，倒序）
    return 30 if (year_info >> (16 - month)) & 1 else 29


def gregorian_to_lunar(year: int, month: int, day: int) -> Tuple[int, int, int, bool]:
    """
    將西曆日期轉換為農曆日期

    Args:
        year: 西曆年份 (1900-2099)
        month: 西曆月份
        day: 西曆日期

    Returns:
        Tuple[int, int, int, bool]: (農曆年, 農曆月, 農曆日, 是否閏月)
    """
    if year < 1900 or year > 2099:
        raise ValueError(f"年份 {year} 超出支援範圍 (1900-2099)")

    target_date = date(year, month, day)
    offset = (target_date - LUNAR_START_DATE).days

    if offset < 0:
        raise ValueError("日期早於1900年1月31日")

    # 逐年計算
    lunar_year = 1900
    year_index = 0

    while year_index < len(YEAR_INFOS):
        year_info = YEAR_INFOS[year_index]
        year_days = _year_days(year_info)

        if offset < year_days:
            break
        offset -= year_days
        lunar_year += 1
        year_index += 1

    if year_index >= len(YEAR_INFOS):
        raise ValueError("日期超出支援範圍")

    # 逐月計算
    year_info = YEAR_INFOS[year_index]
    leap_month = year_info & 0xF

    for m in range(1, 13):
        # 正常月份
        days = _month_days(year_info, m, False)
        if offset < days:
            return (lunar_year, m, offset + 1, False)
        offset -= days

        # 閏月（如果該月有閏月）
        if m == leap_month:
            days = _month_days(year_info, m, True)
            if offset < days:
                return (lunar_year, m, offset + 1, True)
            offset -= days

    # 不應該到達這裡
    raise ValueError("日期計算錯誤")


def lunar_next_day(year: int, month: int, day: int,
                   is_leap: bool = False) -> Tuple[int, int, int, bool]:
    """農曆日期加一天，正確處理月長與閏月轉入。

    子時起卦需要它：原書「日始於子時」，23 時的卦屬次日。
    """
    index = year - 1900
    if not 0 <= index < len(YEAR_INFOS):
        # 超出曆表範圍：僅遞增日數，讓餘數計算仍可進行
        return year, month, day + 1, is_leap

    year_info = YEAR_INFOS[index]
    if day < _month_days(year_info, month, is_leap):
        return year, month, day + 1, is_leap
    # 月末：若本月為正月份且該月有閏，次日進入閏月
    if not is_leap and month == (year_info & 0xF):
        return year, month, 1, True
    if month < 12:
        return year, month + 1, 1, False
    return year + 1, 1, 1, False


# 地支名稱對照
DIZHI = {
    1: "子", 2: "丑", 3: "寅", 4: "卯", 5: "辰", 6: "巳",
    7: "午", 8: "未", 9: "申", 10: "酉", 11: "戌", 12: "亥"
}


def get_year_dizhi(lunar_year: int) -> Tuple[int, str]:
    """
    獲取農曆年的地支數和名稱

    根據梅花易數原典，年數使用地支序數（1-12）
    1900年為庚子年，地支為子(1)
    """
    # 1900年是庚子年，地支為子(1)
    dizhi_num = ((lunar_year - 1900) % 12) + 1
    return dizhi_num, DIZHI[dizhi_num]


def get_shichen(hour: int) -> Tuple[int, str]:
    """獲取時辰數和名稱"""
    return SHICHEN[hour]


def num_to_gua(n: int) -> int:
    """數字轉卦數（餘0當8）"""
    remainder = n % 8
    return 8 if remainder == 0 else remainder


def num_to_yao(n: int) -> int:
    """數字轉動爻數（餘0當6）"""
    remainder = n % 6
    return 6 if remainder == 0 else remainder


def get_hexagram_binary(upper: int, lower: int) -> str:
    """獲取六爻二進位表示"""
    return BAGUA[upper]["binary"] + BAGUA[lower]["binary"]


def apply_change(binary: str, yao_position: int) -> str:
    """應用動爻變化（從下往上數，1-6）"""
    index = 6 - yao_position
    bit_list = list(binary)
    bit_list[index] = "0" if bit_list[index] == "1" else "1"
    return "".join(bit_list)


def binary_to_gua_pair(binary: str) -> Tuple[int, int]:
    """二進位轉上下卦數"""
    return BINARY_TO_GUA[binary[:3]], BINARY_TO_GUA[binary[3:]]


def get_hu_gua(binary: str) -> Tuple[int, int]:
    """計算互卦（取2-4爻為下互，3-5爻為上互）"""
    return BINARY_TO_GUA[binary[1:4]], BINARY_TO_GUA[binary[2:5]]


def get_cuo_gua(binary: str) -> Tuple[int, int]:
    """計算錯卦（陰陽全反：六爻每位翻轉）→ 上下卦數"""
    flipped = "".join("0" if b == "1" else "1" for b in binary)
    return binary_to_gua_pair(flipped)


def get_zong_gua(binary: str) -> Tuple[int, int]:
    """計算綜卦（上下顛倒：整卦翻轉）→ 上下卦數"""
    return binary_to_gua_pair(binary[::-1])


# 五行相生相剋（模組層級，供生剋與旺衰共用同一份真相）
WUXING_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WUXING_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 時令當旺之五行。卦氣依「月建」（以節換月：立春起寅月），不依農曆月份。
# 《梅花易數》卷一〈卦氣旺〉：震巽木旺於春，離火旺於夏，乾兌金旺於秋，
# 坎水旺於冬，坤艮土旺於辰戌丑未月——土旺是整個辰戌丑未月，不是「季末 18 天」。
SEASON_ELEMENT = {"春": "木", "夏": "火", "秋": "金", "冬": "水", "土月": "土"}


def lunar_to_gregorian(year: int, month: int, day: int, is_leap: bool = False) -> date:
    """農曆 → 西曆（查同一份曆表，與 gregorian_to_lunar 互逆）。"""
    index = year - 1900
    if not 0 <= index < len(YEAR_INFOS):
        raise ValueError(f"年份 {year} 超出支援範圍 (1900-2099)")
    offset = sum(_year_days(YEAR_INFOS[i]) for i in range(index))
    info = YEAR_INFOS[index]
    leap = info & 0xF
    if is_leap and leap != month:
        raise ValueError(f"{year} 年無閏{month}月")
    for m in range(1, 13):
        if m == month and not is_leap:
            break
        offset += _month_days(info, m, False)
        if m == leap:
            if m == month and is_leap:
                break
            offset += _month_days(info, m, True)
    if not 1 <= day <= _month_days(info, month, is_leap):
        raise ValueError(f"農曆{year}年{'閏' if is_leap else ''}{month}月沒有{day}日")
    return LUNAR_START_DATE + timedelta(days=offset + day - 1)


def season_at(moment: datetime, tz_hours: float = cal.DEFAULT_TZ_HOURS) -> Tuple[str, str, bool]:
    """起卦時刻 → (時令, 月建, 是否近交節)。"""
    zhi, dist = cal.month_zhi(moment, tz_hours)
    return cal.SEASON_OF_MONTH_ZHI[zhi], zhi, dist < 0.025


def analyze_wangshuai(element: str, season: str) -> str:
    """某五行在該時令的旺相休囚死。

    純推導不查表：當令者旺、令生者相、生令者休、剋令者囚、令剋者死。
    references/yingqi-calc.md §3.1 與 ying-guides.md 第四應各存了一份同樣的表，
    此處改為推導，兩份 markdown 降為說明文件——test_meihua_qigua 會逐格比對，
    三者不同步即測試失敗。
    """
    se = SEASON_ELEMENT[season]
    if element == se:
        return "旺"
    if WUXING_SHENG[se] == element:
        return "相"
    if WUXING_SHENG[element] == se:
        return "休"
    if WUXING_KE[element] == se:
        return "囚"
    if WUXING_KE[se] == element:
        return "死"
    return "未知"


def analyze_wuxing(ti_element: str, yong_element: str) -> str:
    """分析體用五行生克關係"""
    sheng = WUXING_SHENG
    ke = WUXING_KE

    if ti_element == yong_element:
        return "比和（吉）"
    elif sheng.get(yong_element) == ti_element:
        return "用生體（大吉）"
    elif sheng.get(ti_element) == yong_element:
        return "體生用（耗洩）"
    elif ke.get(ti_element) == yong_element:
        return "體克用（吉）"
    elif ke.get(yong_element) == ti_element:
        return "用克體（凶）"
    return "未知關係"


def analyze_guade(ti_gua: int, yong_gua: int) -> str:
    """以卦德交互給出『象的關係』描述（互補於五行生剋，皆為參考透鏡，非判決）。"""
    ti_de, yong_de = BAGUA[ti_gua]["de"], BAGUA[yong_gua]["de"]
    head = (f"你（體・{BAGUA[ti_gua]['name']}）傾向「{GUADE_INTENT[ti_de]}」，"
            f"處境（用・{BAGUA[yong_gua]['name']}）正在「{GUADE_INTENT[yong_de]}」")
    if ti_de == yong_de:
        note = "同德相應，內外方向一致，順勢即可"
    else:
        note = _GUADE_POLAR.get(frozenset({ti_de, yong_de}),
                                "兩股力性質不同，端看你如何在其間取捨")
    return f"{head}。{note}（{ti_de}遇{yong_de}）"


def _yao_name(position: int, is_yang: bool) -> str:
    """爻的傳統名稱，如 初九、六二、九五、上六。"""
    yinyang = "九" if is_yang else "六"
    if position == 1:
        return "初" + yinyang
    if position == 6:
        return "上" + yinyang
    return yinyang + {2: "二", 3: "三", 4: "四", 5: "五"}[position]


def analyze_yao_positions(binary: str, dong_yao: int) -> Dict:
    """結構性爻位盤：六爻當位(得正)/得中/應(對爻)/承乘。

    純結構決定性分析（非文本統計），每次起卦必出。
    binary 為頂到底字串：index0=第6爻(上)，index5=第1爻(初)。

    ※ 出處說明：當位/得中/相應/承乘出自《周易》義理（彖象傳一路的爻位學），
    《梅花易數》原書並不使用。本專案有意加掛這一層作為結構性補充——它是後加的
    透鏡，不是邵雍原法；錯卦/綜卦同理（屬卦變之學）。勿當作原書步驟引述。
    """
    is_yang = {i: binary[6 - i] == "1" for i in range(1, 7)}

    lines = []
    for i in range(1, 7):
        yang = is_yang[i]
        # 當位（得正）：陽居奇位、陰居偶位
        dangwei = (yang and i % 2 == 1) or (not yang and i % 2 == 0)
        # 應（對爻）：初四、二五、三上，一陰一陽為有應
        partner = i + 3 if i <= 3 else i - 3
        lines.append({
            "位": i,
            "名稱": _yao_name(i, yang),
            "陰陽": "陽" if yang else "陰",
            "當位": "得正" if dangwei else "失正",
            "得中": "得中" if i in (2, 5) else "",
            "應位": partner,
            "應爻名稱": _yao_name(partner, is_yang[partner]),
            "有應": is_yang[i] != is_yang[partner],
        })

    # 承乘：相鄰兩爻，標記兩極。標於上爻。
    # 古法「乘」只用於陰居陽上（柔乘剛），故陰乘陽為本名；反之陽居陰上，其古名
    # 是下方之陰「承」上方之陽（陰承陽），並無「陽乘陰」一詞——勿自創該詞。
    # 標記掛在上爻，故以「下陰承陽」點明是下爻在承。
    chengcheng = {}
    for i in range(2, 7):
        if not is_yang[i] and is_yang[i - 1]:
            chengcheng[i] = "陰乘陽（柔凌剛·最不穩）"
        elif is_yang[i] and not is_yang[i - 1]:
            chengcheng[i] = "下陰承陽（柔承剛·最順）"
    for ln in lines:
        ln["承乘"] = chengcheng.get(ln["位"], "")

    # 二五中正相應：二有應且二五皆得正——最強外援徵象
    er, wu = lines[1], lines[4]
    zhongzheng = er["有應"] and er["當位"] == "得正" and wu["當位"] == "得正"

    # 動爻處境摘要
    d = lines[dong_yao - 1]
    parts = [d["當位"]]
    parts.append("有應" if d["有應"] else f"無應(↔{d['應爻名稱']}同性)")
    if d["承乘"]:
        parts.append(d["承乘"])
    # 動爻是否被上爻陰乘（柔凌剛壓於其上）
    if dong_yao < 6 and chengcheng.get(dong_yao + 1, "").startswith("陰乘陽"):
        parts.append(f"上被{lines[dong_yao]['名稱']}陰乘")
    dong_summary = f"{d['名稱']}（動）：" + "·".join(parts)

    return {
        "六爻": lines,
        "二五中正相應": zhongzheng,
        "動爻摘要": dong_summary,
    }


def _relation_to_ti(ti_element: str, other_element: str) -> str:
    """他卦五行對體卦的作用：生體/克體/比和/體生（洩）/體克（耗）。"""
    if other_element == ti_element:
        return "比和"
    if WUXING_SHENG[other_element] == ti_element:
        return "生體"
    if WUXING_KE[other_element] == ti_element:
        return "克體"
    if WUXING_SHENG[ti_element] == other_element:
        return "體生（洩）"
    return "體克（耗）"


# 生體、比和為「體黨」（助我）；克體、體生（洩我）為「用黨」（損我）；
# 體克他卦＝我能制之，可得而費力（原書「體克用，吉，但遲」）。
_TI_SCORE = {"生體": 2, "比和": 1, "體克（耗）": 0.5, "體生（洩）": -1, "克體": -2}


def analyze_ti_dang(ti_gua: int, yong_gua: int, hu_upper: int, hu_lower: int,
                    bian_changed: int, ti_state: Optional[str]) -> Dict:
    """《梅花易數》體用總訣的整卦判斷：用、互、變三層對體卦的生克。

    原書〈體用總訣〉：「體用之說……互卦、變卦，生體者吉，克體者凶」；
    又「體之卦氣宜盛不宜衰」。這裡把三層關係逐一列出，並給一個方向性的
    總評，讓解卦有據可查，而不只看用卦一處。
    """
    ti_el = BAGUA[ti_gua]["element"]
    layers = [
        ("用卦（近）", yong_gua),
        ("互卦上（中）", hu_upper),
        ("互卦下（中）", hu_lower),
        ("變卦之用（遠）", bian_changed),
    ]
    rows = []
    score = 0.0
    for label, g in layers:
        rel = _relation_to_ti(ti_el, BAGUA[g]["element"])
        rows.append({"層": label, "卦": BAGUA[g]["name"], "五行": BAGUA[g]["element"], "對體": rel})
        weight = 1.5 if label.startswith("用") or label.startswith("變") else 1.0
        score += _TI_SCORE[rel] * weight
    if ti_state in ("旺", "相"):
        score += 1
    elif ti_state in ("囚", "死"):
        score -= 1
    if score >= 3:
        verdict = "整體偏吉：助體之力明顯多於損體之力"
    elif score >= 1:
        verdict = "小吉：有助力，但非一路順風"
    elif score >= 0.5:
        verdict = "略偏吉：助力稍多，但得失互見"
    elif score > -0.5:
        verdict = "吉凶參半：得失互見，成敗看人為"
    elif score > -1:
        verdict = "略偏凶：耗損稍多，宜謹慎"
    elif score > -3:
        verdict = "偏凶：阻力或耗損大於助力，宜緩、宜守、宜調整做法"
    else:
        verdict = "凶象明顯：多方克洩體卦，此事不宜硬推"
    return {"各層": rows, "分數": round(score, 1), "總評": verdict}


def _analyze_hexagram(upper_gua: int, lower_gua: int, dong_yao: int,
                      shiling: Optional[Dict] = None) -> Dict:
    """分析卦象（本卦、體用、互卦、變卦）。

    shiling 為 {"時令","月建","近交節"}（見 season_at）；有占時才輸出【卦氣旺衰】。
    純數字起卦而不給占時，就沒有月令可據，該節從缺——不拿今天的日期去猜。
    """
    hexagram_binary = get_hexagram_binary(upper_gua, lower_gua)
    hexagram_info = HEXAGRAMS.get((upper_gua, lower_gua), (0, "未知卦"))

    # 體用：動爻所在之卦為用，不動之卦為體
    if dong_yao > 3:
        ti_gua, yong_gua = lower_gua, upper_gua
        ti_pos, yong_pos = "下卦", "上卦"
    else:
        ti_gua, yong_gua = upper_gua, lower_gua
        ti_pos, yong_pos = "上卦", "下卦"

    bian_binary = apply_change(hexagram_binary, dong_yao)
    bian_upper, bian_lower = binary_to_gua_pair(bian_binary)
    bian_info = HEXAGRAMS.get((bian_upper, bian_lower), (0, "未知卦"))
    bian_changed = bian_upper if dong_yao > 3 else bian_lower  # 用卦變成的那個卦

    # 互卦。乾、坤六爻皆同，互卦得本卦自身，原書改從變卦取互。
    hu_from_bian = hexagram_binary in ("111111", "000000")
    hu_upper, hu_lower = get_hu_gua(bian_binary if hu_from_bian else hexagram_binary)
    hu_info = HEXAGRAMS.get((hu_upper, hu_lower), (0, "未知卦"))

    cuo_upper, cuo_lower = get_cuo_gua(hexagram_binary)
    cuo_info = HEXAGRAMS.get((cuo_upper, cuo_lower), (0, "未知卦"))
    zong_upper, zong_lower = get_zong_gua(hexagram_binary)
    zong_info = HEXAGRAMS.get((zong_upper, zong_lower), (0, "未知卦"))

    moving_is_yang = hexagram_binary[6 - dong_yao] == "1"
    ti_element = BAGUA[ti_gua]["element"]
    yong_element = BAGUA[yong_gua]["element"]

    ti_state = None
    if shiling:
        ti_state = analyze_wangshuai(ti_element, shiling["時令"])

    out = {
        "本卦": {
            "序號": hexagram_info[0],
            "名稱": hexagram_info[1],
            "上卦": f"{BAGUA[upper_gua]['name']} {BAGUA[upper_gua]['symbol']}",
            "下卦": f"{BAGUA[lower_gua]['name']} {BAGUA[lower_gua]['symbol']}",
            "二進位": hexagram_binary,
            "動爻": f"第{dong_yao}爻",
            "動爻位": dong_yao,
            "動爻陰陽": "陽" if moving_is_yang else "陰",
            "動爻名": _yao_name(dong_yao, moving_is_yang),
        },
        "體用": {
            "體卦": f"{BAGUA[ti_gua]['name']}（{ti_pos}）- {ti_element}・{BAGUA[ti_gua]['de']}",
            "用卦": f"{BAGUA[yong_gua]['name']}（{yong_pos}）- {yong_element}・{BAGUA[yong_gua]['de']}",
            "生克關係": analyze_wuxing(ti_element, yong_element),
            "卦德關係": analyze_guade(ti_gua, yong_gua),
        },
        "體用總訣": analyze_ti_dang(ti_gua, yong_gua, hu_upper, hu_lower, bian_changed, ti_state),
        "爻位盤": analyze_yao_positions(hexagram_binary, dong_yao),
        "互卦": {
            "名稱": hu_info[1],
            "上互": BAGUA[hu_upper]['name'],
            "下互": BAGUA[hu_lower]['name'],
            "取自變卦": hu_from_bian,
        },
        "變卦": {
            "序號": bian_info[0],
            "名稱": bian_info[1],
            "二進位": bian_binary,
            "用之變": BAGUA[bian_changed]["name"],
        },
        "錯卦": {
            "名稱": cuo_info[1],
            "上卦": BAGUA[cuo_upper]['name'],
            "下卦": BAGUA[cuo_lower]['name'],
            "讀法": "陰陽全反——同一處境的完全相反面，照出你沒看到的另一端",
        },
        "綜卦": {
            "名稱": zong_info[1],
            "上卦": BAGUA[zong_upper]['name'],
            "下卦": BAGUA[zong_lower]['name'],
            "讀法": "上下顛倒——換對方/旁觀者的角度看同一件事",
        },
    }
    if shiling:
        season = shiling["時令"]
        out["卦氣旺衰"] = {
            "時令": f"{shiling['月建']}月・{season}（{SEASON_ELEMENT[season]}旺）",
            "體卦旺衰": f"{BAGUA[ti_gua]['name']}{ti_element}・{ti_state}",
            "用卦旺衰": f"{BAGUA[yong_gua]['name']}{yong_element}・"
                     f"{analyze_wangshuai(yong_element, season)}",
            "體卦得令": ti_state in ("旺", "相"),
            "近交節": shiling.get("近交節", False),
            "讀法": "體卦旺相則事易成、可為；休囚死則力弱、宜緩。"
                  "旺相加吉、休囚減力——為程度修正，非獨立吉凶。",
        }
    out.update(_analyze_dang_xiang_yingqi(
        ti_gua, [("用卦", yong_gua), ("互卦上", hu_upper), ("互卦下", hu_lower), ("變卦之用", bian_changed)],
        upper_gua, lower_gua, shiling))
    return out


_XIANG_KEYS = ("人物", "身體", "動物", "物品", "方位", "時辰", "數字")
_XIANG_CACHE: Optional[Dict[str, Dict[str, str]]] = None


def load_bagua_xiang() -> Dict[str, Dict[str, str]]:
    """八卦類象：直接讀 references/bagua-wanwu.md 各卦開頭的「基本屬性／類象」，不在程式裡另存一份。

    找不到參考檔（例如單獨複製腳本）時回傳空表，類象一節從缺。
    """
    global _XIANG_CACHE
    if _XIANG_CACHE is not None:
        return _XIANG_CACHE
    import os
    import re
    table: Dict[str, Dict[str, str]] = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "bagua-wanwu.md")
    try:
        with open(path, encoding="utf-8") as f:
            current = None
            for line in f:
                line = line.strip()
                m = re.match(r"^([乾兌離震巽坎艮坤])卦 [☰☱☲☳☴☵☶☷]", line)
                if m:
                    current = table.setdefault(m.group(1), {})
                    if len(table) > 8:
                        break
                    continue
                if current is None or "：" not in line:
                    continue
                key, val = line.split("：", 1)
                if key in _XIANG_KEYS and key not in current:
                    current[key] = val.replace("（後天）", "")
    except OSError:
        table = {}
    _XIANG_CACHE = table
    return table


def _analyze_dang_xiang_yingqi(ti_gua: int, layers: List[Tuple[str, int]], upper_gua: int, lower_gua: int,
                               shiling: Optional[Dict]) -> Dict:
    """克體／生體之黨、各卦旺衰、類象、應期——供斷「成敗輕重」「應在何事」「何時應」。

    原書依據：
    - 觀梅占：「兌金為體，離火克之。互中巽木，復三起離火，則克體之卦氣盛。」——他卦生克體之卦，為其黨。
    - 體用總訣：體之卦氣宜盛；克體之卦宜衰。故各卦都列旺衰。
    - 老人有憂色占：「行則應速，以其成卦之數中分而取其半；坐則應遲，增倍而取之；立則半遲半速，只以成卦之數取之。」
    - 求財占：「欲知得財之日，生體之卦氣定之；欲知破財之日，克體之卦氣定之。」他占類推。
    這裡只整理，不下斷語。
    """
    ti_el = BAGUA[ti_gua]["element"]
    season = shiling["時令"] if shiling else None
    rows = []
    for label, g in layers:
        el = BAGUA[g]["element"]
        rows.append({"層": label, "卦": BAGUA[g]["name"], "五行": el, "對體": _relation_to_ti(ti_el, el),
                     "旺衰": analyze_wangshuai(el, season) if season else None, "gua": g})
    dang = []
    for r in rows:
        if r["對體"] not in ("克體", "生體"):
            continue
        helpers = [o for o in rows if o is not r and WUXING_SHENG[o["五行"]] == r["五行"]]
        checks = [o for o in rows if o is not r and WUXING_KE[o["五行"]] == r["五行"]]
        txt = f"{r['對體']}之卦：{r['卦']}{r['五行']}（{r['層']}）" + (f"・{r['旺衰']}" if r["旺衰"] else "")
        if helpers:
            txt += "；得" + "、".join(f"{o['卦']}{o['五行']}（{o['層']}）" for o in helpers) + "相生，其勢更盛"
        if checks:
            txt += "；被" + "、".join(f"{o['卦']}{o['五行']}（{o['層']}）" for o in checks) + "所克，其力受制"
        dang.append(txt)
    if not dang:
        dang.append("用、互、變皆無生體、克體之卦：只論比和與體生、體克")
    xiang_table = load_bagua_xiang()
    xiang = []
    seen = set()
    for r in rows:
        if r["卦"] in seen or r["卦"] not in xiang_table:
            continue
        seen.add(r["卦"])
        x = xiang_table[r["卦"]]
        xiang.append(f"{r['卦']}（{r['層']}・{r['對體']}）：" + "；".join(f"{k} {x[k]}" for k in _XIANG_KEYS if k in x))
    yingqi: Dict[str, object] = {}
    if shiling and shiling.get("時支數"):
        n = upper_gua + lower_gua + shiling["時支數"]
        yingqi["卦數"] = (f"上卦{upper_gua}＋下卦{lower_gua}＋{shiling['時支']}時{shiling['時支數']}＝{n}："
                         f"行中問者取半 {n / 2:g}、立者如數 {n}、坐者加倍 {n * 2}（單位依事之遠近：時、日、月）")
    for r in rows:
        if r["對體"] in ("克體", "生體") and r["卦"] in xiang_table:
            x = xiang_table[r["卦"]]
            kind = "吉期（生體之卦氣）" if r["對體"] == "生體" else "凶期（克體之卦氣）"
            yingqi.setdefault(kind, [])
            item = f"{r['卦']}{r['五行']}：{x.get('時辰', '')}年月日時，或{r['五行']}旺之月日"
            if item not in yingqi[kind]:
                yingqi[kind].append(item)
    out: Dict[str, object] = {"生克之黨": dang}
    if season:
        out["各卦旺衰"] = [f"{r['層']} {r['卦']}{r['五行']}・{r['旺衰']}（{r['對體']}）" for r in rows]
    if xiang:
        out["類象"] = xiang
    if yingqi:
        out["應期"] = yingqi
    return out


def _apply_zishi(year: int, month: int, day: int, hour: int,
                 is_leap: bool) -> Tuple[int, int, int, bool, bool]:
    """原書「日始於子時」：23 時已入次日子時，日數取次日。

    唯一的推日處。夜子時一派主張仍算當日——本專案取日始於子時，此為明確取捨。
    """
    if hour != 23:
        return year, month, day, is_leap, False
    year, month, day, is_leap = lunar_next_day(year, month, day, is_leap)
    return year, month, day, is_leap, True


def _shiling(moment: Optional[datetime], tz_hours: float) -> Optional[Dict]:
    if moment is None:
        return None
    season, zhi, near = season_at(moment, tz_hours)
    shichen_num, shichen_name = get_shichen(moment.hour)
    return {"時令": season, "月建": zhi, "近交節": near, "時支數": shichen_num, "時支": shichen_name}


def qigua_by_time(year: int, month: int, day: int, hour: int,
                  is_leap: bool = False, moment: Optional[datetime] = None,
                  tz_hours: float = cal.DEFAULT_TZ_HOURS) -> Dict:
    """以農曆年月日時起卦（邵雍原法）。

    上卦＝(年支數+月+日)÷8；下卦＝(年支數+月+日+時支數)÷8；動爻＝同總數÷6。
    moment 為起卦的西曆鐘面時刻（用來定月建／卦氣）；省略則由農曆日反推。
    """
    if moment is None:
        g = lunar_to_gregorian(year, month, day, is_leap)
        moment = datetime(g.year, g.month, g.day, hour, 0)
    year, month, day, is_leap, rolled = _apply_zishi(year, month, day, hour, is_leap)
    year_num, year_dizhi = get_year_dizhi(year)
    shichen_num, shichen_name = get_shichen(hour)

    upper_sum = year_num + month + day
    lower_sum = upper_sum + shichen_num

    upper_gua = num_to_gua(upper_sum)
    lower_gua = num_to_gua(lower_sum)
    dong_yao = num_to_yao(lower_sum)

    result = _analyze_hexagram(upper_gua, lower_gua, dong_yao, _shiling(moment, tz_hours))
    result["計算過程"] = {
        "年數": f"{year_dizhi}年 ({year_num})",
        "月數": f"{'閏' if is_leap else ''}{month}",
        "日數": day,
        "時辰": f"{shichen_name}時 ({shichen_num})",
        "上卦數": f"(年+月+日)={upper_sum} mod 8 = {upper_gua} → {BAGUA[upper_gua]['name']}",
        "下卦數": f"(年+月+日+時)={lower_sum} mod 8 = {lower_gua} → {BAGUA[lower_gua]['name']}",
        "動爻數": f"{lower_sum} mod 6 = {dong_yao}",
        "方法": "邵雍原法（年月日時）",
    }
    if rolled:
        result["計算過程"]["子時推日"] = "日始於子時，23時已入次日，日數取次日"
    return result


def _lunar_display(year: int, month: int, day: int, hour: int,
                   is_leap: bool) -> Tuple[str, bool]:
    """顯示「實際起卦所用」的農曆日，即子時推日之後的那一天。"""
    y, m, d, leap, rolled = _apply_zishi(year, month, day, hour, is_leap)
    return f"{y}年{'閏' if leap else ''}{m}月{d}日", rolled


def qigua_by_gregorian_time(year: int, month: int, day: int, hour: int,
                            minute: int = 0,
                            tz_hours: float = cal.DEFAULT_TZ_HOURS) -> Dict:
    """以西曆時間起卦（自動轉換為農曆；邵雍原法）"""
    lunar_year, lunar_month, lunar_day, is_leap = gregorian_to_lunar(year, month, day)
    moment = datetime(year, month, day, hour, minute)
    result = qigua_by_time(lunar_year, lunar_month, lunar_day, hour, is_leap,
                           moment=moment, tz_hours=tz_hours)

    lunar_text, rolled = _lunar_display(lunar_year, lunar_month, lunar_day, hour, is_leap)
    note = "梅花易數使用農曆計算；卦氣依節氣月建"
    if rolled:
        note += "；23時屬次日子時，農曆日已推次日（日始於子時）"
    result["日期轉換"] = {
        "西曆": f"{year}年{month}月{day}日 {hour:02d}:{minute:02d}",
        "農曆": lunar_text,
        "說明": note,
    }
    return result


def qigua_by_time_precise(year: int, month: int, day: int,
                          hour: int, minute: int, second: int,
                          is_leap: bool = False, moment: Optional[datetime] = None,
                          tz_hours: float = cal.DEFAULT_TZ_HOURS) -> Dict:
    """以農曆時間 + 分秒起卦（今人擴充，非邵雍原法；僅在用戶明確要求時使用）。

    上卦＝(年+月+日+時)÷8、下卦＝(上數+分)÷8、動爻＝(下數+秒)÷6。
    注意：此法連上卦都與原法不同，兩者不可混稱。
    """
    if moment is None:
        g = lunar_to_gregorian(year, month, day, is_leap)
        moment = datetime(g.year, g.month, g.day, hour, minute, second)
    year, month, day, is_leap, rolled = _apply_zishi(year, month, day, hour, is_leap)
    year_num, year_dizhi = get_year_dizhi(year)
    shichen_num, shichen_name = get_shichen(hour)

    upper_sum = year_num + month + day + shichen_num
    lower_sum = upper_sum + minute
    dong_sum = lower_sum + second

    upper_gua = num_to_gua(upper_sum)
    lower_gua = num_to_gua(lower_sum)
    dong_yao = num_to_yao(dong_sum)

    result = _analyze_hexagram(upper_gua, lower_gua, dong_yao, _shiling(moment, tz_hours))
    result["計算過程"] = {
        "年數": f"{year_dizhi}年 ({year_num})",
        "月數": month,
        "日數": day,
        "時辰": f"{shichen_name}時 ({shichen_num})",
        "分": minute,
        "秒": second,
        "上卦數": f"(年+月+日+時辰)={upper_sum} mod 8 = {upper_gua}",
        "下卦數": f"(上+分)={lower_sum} mod 8 = {lower_gua}",
        "動爻數": f"(下+秒)={dong_sum} mod 6 = {dong_yao}",
        "方法": "⚠ 今人分秒擴充，非邵雍原法",
    }
    if rolled:
        result["計算過程"]["子時推日"] = "日始於子時，23時已入次日，日數取次日"
    return result


def qigua_by_gregorian_time_precise(year: int, month: int, day: int,
                                    hour: int, minute: int, second: int,
                                    tz_hours: float = cal.DEFAULT_TZ_HOURS) -> Dict:
    """以西曆時間 + 分秒起卦（自動轉農曆；今人擴充）。"""
    lunar_year, lunar_month, lunar_day, is_leap = gregorian_to_lunar(year, month, day)
    moment = datetime(year, month, day, hour, minute, second)
    result = qigua_by_time_precise(lunar_year, lunar_month, lunar_day,
                                   hour, minute, second, is_leap,
                                   moment=moment, tz_hours=tz_hours)
    lunar_text, rolled = _lunar_display(lunar_year, lunar_month, lunar_day, hour, is_leap)
    note = "分秒為今人擴充，非原法"
    if rolled:
        note += "；23時屬次日子時，農曆日已推次日（日始於子時）"
    result["日期轉換"] = {
        "西曆": f"{year}年{month}月{day}日 {hour:02d}:{minute:02d}:{second:02d}",
        "農曆": lunar_text,
        "說明": note,
    }
    return result


def qigua_by_numbers(num1: int, num2: int, num3: Optional[int] = None,
                     shiling: Optional[Dict] = None,
                     add_hour: Optional[int] = None) -> Dict:
    """以數字起卦。

    上卦＝第一數÷8、下卦＝第二數÷8；動爻＝所報數總和÷6（原書總數除六）。
    add_hour 為時支數（1–12）：若用戶要「加時」的派別（物數/聲音占之例），
    動爻改為 (總和＋時數)÷6；預設不加。
    """
    upper_gua = num_to_gua(num1)
    lower_gua = num_to_gua(num2)
    nums = [num1, num2] + ([num3] if num3 is not None else [])
    total = sum(nums) + (add_hour or 0)
    dong_yao = num_to_yao(total)

    result = _analyze_hexagram(upper_gua, lower_gua, dong_yao, shiling)
    expr = "+".join(str(n) for n in nums) + (f"+時{add_hour}" if add_hour else "")
    result["計算過程"] = {
        "第一數": f"{num1} → {num1} mod 8 = {upper_gua} → {BAGUA[upper_gua]['name']}",
        "第二數": f"{num2} → {num2} mod 8 = {lower_gua} → {BAGUA[lower_gua]['name']}",
        "動爻": f"({expr})={total} mod 6 = {dong_yao}",
    }
    return result


def qigua_by_numbers_at(year: int, month: int, day: int, hour: int,
                        num1: int, num2: int,
                        num3: Optional[int] = None, minute: int = 0,
                        add_hour: bool = False,
                        tz_hours: float = cal.DEFAULT_TZ_HOURS) -> Dict:
    """數字起卦 + 占時（西曆鐘面時間），使【卦氣旺衰】可用。

    占時只定月建（卦氣），不入上下卦；add_hour=True 時才把時支數加入動爻。
    """
    moment = datetime(year, month, day, hour, minute)
    shichen_num, shichen_name = get_shichen(hour)
    result = qigua_by_numbers(num1, num2, num3, _shiling(moment, tz_hours),
                              shichen_num if add_hour else None)
    lunar_year, lunar_month, lunar_day, is_leap = gregorian_to_lunar(year, month, day)
    lunar_text, _ = _lunar_display(lunar_year, lunar_month, lunar_day, hour, is_leap)
    result["計算過程"]["占時"] = (f"西曆{year}年{month}月{day}日 {hour:02d}:{minute:02d}"
                              f"（農曆{lunar_text}，{shichen_name}時）——定月建／卦氣"
                              + ("，並加時數入動爻" if add_hour else "，不入起卦之數"))
    return result


# ==============================================================================
# 文本指標輔助功能 (Text-Metric Helpers)
#
# 出處：姊妹專案 muyen/decoding-iching 對 384 條爻辭的語言分析（吉語/凶語密度、
# 文本嵌入相似度）。以下百分比是「爻辭吉語比例」——衡量該卦爻辭講得多正面，
# 不是現實世界的成功機率，切勿以「吉率」之名輸出給用戶。
#
# 保留範圍的說明：該專案已撤回卦層級分類的統計顯著性主張（每卦僅 n=6 爻，
# 隨機置換標籤得同等極端的「吸引子/排斥子」，p=0.35/0.52）。本專案仍保留這一層
# 作為「爻辭語氣排序」的參考，並在 SKILL.md 與 hexagram-strategy.md 標明性質；
# 留/走/守/變/慎/觀 與變卦路徑本身屬義理判斷，不依賴該統計主張。
#
# 不影響起卦邏輯。
# ==============================================================================

# 爻位係數（Position Coefficients）
POSITION_COEFFICIENTS = {
    5: 0.422,   # ★★ 最佳（九五之尊）
    2: 0.344,   # ★ 佳（得中）
    4: 0.266,   # 中
    1: 0.234,   # 中
    6: 0.031,   # 差
    3: -0.219,  # ✗✗ 最差（三多凶）
}

# 爻位 × 陰陽係數
POSITION_YINYANG_COEFFICIENTS = {
    # (position, is_yang): coefficient
    (1, True): 0.281, (1, False): 0.188,
    (2, True): 0.312, (2, False): 0.375,
    (3, True): -0.375, (3, False): -0.062,  # 三位陽爻最凶!
    (4, True): 0.281, (4, False): 0.250,
    (5, True): 0.344, (5, False): 0.500,
    (6, True): 0.000, (6, False): 0.062,
}

# 64卦策略分類
# 類型: 吸引子(留), 排斥子(走), 福地(守), 困境(變), 陷阱(慎), 一般(觀)
# 變卦路徑「變N爻」一律以自下而上的爻位表示（初爻=1 … 上爻=6），
# 與 apply_change / print_result 的爻位約定一致。test_meihua_qigua.py
# 的 TestStrategyChangePaths 會驗證每條路徑的變爻確實能將本卦變為目標卦。
HEXAGRAM_STRATEGY = {
    1: ("排斥子", "走", 0, "乾 → 履（變3爻得50%）"),
    2: ("一般", "觀", 33, "坤 → 謙（變3爻得83%）"),
    3: ("一般", "觀", 33, "屯 → 比（變1爻得67%）"),
    4: ("一般", "觀", 33, "蒙 → 損（變1爻得50%）"),
    5: ("吸引子", "留", 67, None),
    6: ("吸引子", "留", 67, None),
    7: ("排斥子", "走", 17, "師 → 臨（變1爻得83%）"),
    8: ("吸引子", "留", 67, None),
    9: ("一般", "觀", 33, "小畜 → 家人（變2爻得67%）"),
    10: ("福地", "守", 50, None),
    11: ("一般", "觀", 33, "泰 → 臨（變3爻得83%）"),
    12: ("福地", "守", 50, None),
    13: ("排斥子", "走", 17, "同人 → 遯（變1爻得67%）"),
    14: ("一般", "觀", 33, "大有 → 鼎（變1爻得67%）"),
    15: ("吸引子", "留", 83, None),  # 謙卦 - 唯一全吉卦
    16: ("困境", "變", 17, "豫 → 晉（變6爻得67%）"),
    17: ("一般", "觀", 33, "隨 → 萃（變1爻得50%）"),
    18: ("排斥子", "走", 17, "蠱 → 鼎（變4爻得67%）"),
    19: ("吸引子", "留", 83, None),  # 臨卦 - 關鍵轉折點
    20: ("排斥子", "走", 0, "觀 → 比（變6爻得67%）"),
    21: ("排斥子", "走", 17, "噬嗑 → 晉（變1爻得67%）"),
    22: ("一般", "觀", 33, "賁 → 家人（變5爻得67%）"),
    23: ("困境", "變", 17, "剝 → 晉（變4爻得67%）"),
    24: ("一般", "觀", 33, "復 → 臨（變2爻得83%）"),
    25: ("一般", "觀", 33, "无妄 → 否（變1爻得50%）"),
    26: ("福地", "守", 50, None),
    27: ("福地", "守", 50, None),
    28: ("一般", "觀", 33, "大過 → 夬（變1爻）→ 革（變2爻得50%）"),
    29: ("排斥子", "走", 0, "坎 → 比（變2爻得67%）"),
    30: ("一般", "觀", 33, "離 → 豐（變6爻得50%）"),
    31: ("困境", "變", 17, "咸 → 遯（變6爻得67%）"),
    32: ("排斥子", "走", 0, "恆 → 升（變4爻得67%）"),
    33: ("吸引子", "留", 67, None),
    34: ("吸引子", "留", 50, None),
    35: ("吸引子", "留", 67, None),
    36: ("排斥子", "走", 17, "明夷 → 謙（變1爻得83%）"),
    37: ("吸引子", "留", 67, None),
    38: ("一般", "觀", 33, "睽 → 未濟（變1爻得50%）"),
    39: ("排斥子", "走", 17, "蹇 → 謙（變5爻得83%）"),
    40: ("吸引子", "留", 50, None),
    41: ("福地", "守", 50, None),
    42: ("福地", "守", 50, None),
    43: ("排斥子", "走", 0, "夬 → 需（變4爻得67%）"),
    44: ("排斥子", "走", 17, "姤 → 遯（變2爻得67%）"),
    45: ("福地", "守", 50, None),
    46: ("吸引子", "留", 67, None),
    47: ("排斥子", "走", 17, "困 → 訟（變6爻得67%）"),
    48: ("困境", "變", 17, "井 → 需（變1爻得67%）"),
    49: ("吸引子", "留", 50, None),
    50: ("吸引子", "留", 67, None),
    51: ("陷阱", "慎", 17, "震 → 豐（變3爻得50%）"),
    52: ("一般", "觀", 33, "艮 → 謙（變6爻得83%）"),
    53: ("福地", "守", 50, None),
    54: ("一般", "觀", 33, "歸妹 → 臨（變4爻得83%）"),
    55: ("吸引子", "留", 50, None),
    56: ("排斥子", "走", 0, "旅 → 鼎（變2爻得67%）"),
    57: ("一般", "觀", 33, "巽 → 漸（變2爻得50%）"),
    58: ("吸引子", "留", 50, None),
    59: ("一般", "觀", 33, "渙 → 訟（變4爻得67%）"),
    60: ("排斥子", "走", 17, "節 → 臨（變5爻得83%）"),
    61: ("排斥子", "走", 17, "中孚 → 益（變2爻得50%）"),
    62: ("排斥子", "走", 0, "小過 → 謙（變4爻得83%）"),
    63: ("排斥子", "走", 0, "既濟 → 需（變2爻得67%）"),
    64: ("福地", "守", 50, None),
}


def get_position_risk(position: int, is_yang: bool = True) -> dict:
    """
    獲取爻位風險評估

    Args:
        position: 動爻位置 (1-6)
        is_yang: 動爻是否為陽爻

    Returns:
        dict: {
            'coefficient': 係數,
            'risk_level': 風險等級,
            'warning': 警告信息（若有）
        }
    """
    coef = POSITION_YINYANG_COEFFICIENTS.get((position, is_yang), 0)

    if position == 3 and is_yang:
        return {
            'coefficient': coef,
            'risk_level': '高風險',
            'warning': '⚠️ 三位陽爻是全表最凶的組合（-0.375）'
        }
    elif position == 5:
        return {
            'coefficient': coef,
            'risk_level': '最佳',
            'warning': None
        }
    elif position == 2:
        return {
            'coefficient': coef,
            'risk_level': '佳',
            'warning': None
        }
    elif coef < 0:
        return {
            'coefficient': coef,
            'risk_level': '較差',
            'warning': f'⚠️ 爻位係數為負值 ({coef:.3f})'
        }
    else:
        return {
            'coefficient': coef,
            'risk_level': '中等',
            'warning': None
        }


def get_hexagram_strategy(hex_num: int) -> dict:
    """
    獲取卦的策略建議

    Args:
        hex_num: 卦序 (1-64)

    Returns:
        dict: {
            'type': 類型（吸引子/排斥子/福地/困境/陷阱/一般）,
            'advice': 建議（留/走/守/變/慎/觀）,
            'ji_rate': 爻辭吉語比例（文本指標，非成功機率；欄名保留向後相容）,
            'change_path': 推薦變卦路徑（若有）
        }
    """
    if hex_num not in HEXAGRAM_STRATEGY:
        return None

    type_, advice, ji_rate, change_path = HEXAGRAM_STRATEGY[hex_num]
    return {
        'type': type_,
        'advice': advice,
        'ji_rate': ji_rate,
        'change_path': change_path
    }


STRATEGY_NEXT_STEPS = {
    "留": "【下一步】維持現狀，不宜改變。目前位置有利，變動反而損失。",
    "走": "【下一步】積極改變，離開當前狀態。此位置不利久留，宜主動求變。",
    "守": "【下一步】穩守不動，靜觀其變。位置尚可，不主動出擊，等待時機。",
    "變": "【下一步】必須改變，不變則困。當前困境需主動突破，猶豫更糟。",
    "慎": "【下一步】謹慎行事，小心陷阱。周圍環境不佳，任何動作都要三思。",
    "觀": "【下一步】觀察局勢，再做決定。情況中等，需要更多信息才能判斷。",
}


def print_strategy_advice(hex_num: int):
    """打印卦的策略建議"""
    strategy = get_hexagram_strategy(hex_num)
    if not strategy:
        return

    print("\n【策略建議】")
    print(f"  類型：{strategy['type']}")
    print(f"  建議：{strategy['advice']}")
    print(f"  爻辭吉語比例：{strategy['ji_rate']}%（文本指標，非成功機率）")
    if strategy['change_path']:
        print(f"  變卦路徑：{strategy['change_path']}")

    # 輸出具體下一步建議
    advice = strategy['advice']
    if advice in STRATEGY_NEXT_STEPS:
        print(f"\n{STRATEGY_NEXT_STEPS[advice]}")


def print_result(result: Dict):
    """格式化輸出結果"""
    print("\n" + "=" * 50)
    print("📿 梅花易數起卦結果")
    print("=" * 50)

    if "日期轉換" in result:
        conv = result["日期轉換"]
        print("\n【日期轉換】")
        print(f"  {conv['西曆']} → 農曆 {conv['農曆']}（{conv['說明']}）")

    print("\n【一、起卦計算】")
    for key, value in result["計算過程"].items():
        print(f"  {key}：{value}")

    ben = result["本卦"]
    print("\n【二、本卦】")
    print(f"  第 {ben['序號']} 卦：{ben['名稱']}（上{ben['上卦']} 下{ben['下卦']}）")
    print(f"  動爻：{ben['動爻']}（{ben['動爻名']}）")
    try:
        import yaoci_lookup as yl
        print(f"  ▶ 爻辭（第一步・原書先看爻辭）：{yl.format_line(ben['序號'], ben['動爻位'])}")
        print(f"  ▶ {yl.format_guaci(ben['序號'])}")
    except OSError:
        print("  （爻辭檔不在，請查 references/yaoci.md）")

    print("\n【三、體用分析】")
    ty = result["體用"]
    print(f"  體卦（自己）：{ty['體卦']}")
    print(f"  用卦（所問之事）：{ty['用卦']}")
    print(f"  體用生克：{ty['生克關係']}")
    print(f"  卦德：{ty['卦德關係']}")

    if "卦氣旺衰" in result:
        ws = result["卦氣旺衰"]
        print("\n【四、卦氣旺衰】")
        print(f"  時令：{ws['時令']}")
        print(f"  體：{ws['體卦旺衰']}　用：{ws['用卦旺衰']}")
        print(f"  {'體卦得令' if ws['體卦得令'] else '體卦失令'}——{ws['讀法']}")
        if ws.get("近交節"):
            print("  ⚠ 起卦時刻距交節不到約 30 分鐘，月建可能有一個月之差，旺衰判斷宜保守。")
    else:
        print("\n【四、卦氣旺衰】未提供占時，從缺（勿自行代入日期猜測）")

    hu = result["互卦"]
    bian = result["變卦"]
    print("\n【五、互卦（中程・過程）】")
    src = "（本卦六爻皆同，依原書改從變卦取互）" if hu.get("取自變卦") else ""
    print(f"  {hu['名稱']}（上{hu['上互']}下{hu['下互']}）{src}")
    print("\n【六、變卦（遠程・結果）】")
    print(f"  第 {bian['序號']} 卦：{bian['名稱']}（用卦變為{bian['用之變']}）")
    try:
        import yaoci_lookup as yl
        print(f"  ▶ {yl.format_guaci(bian['序號'])}")
    except OSError:
        pass

    if "體用總訣" in result:
        tz = result["體用總訣"]
        print("\n【七、體用總訣（用→互→變，逐層看對體的生克）】")
        for r in tz["各層"]:
            print(f"  {r['層']}：{r['卦']}{r['五行']} → {r['對體']}")
        print(f"  ⇒ {tz['總評']}（方向分 {tz['分數']:+}；為整理用的方向指標，最終以爻辭與事理為準）")

    if "生克之黨" in result:
        print("\n【七之二、克體生體之黨與各卦旺衰（原書：克體之卦氣盛則凶重，生體之卦受制則吉輕）】")
        for line in result["生克之黨"]:
            print(f"  {line}")
        if result.get("各卦旺衰"):
            print("  各卦旺衰：" + "；".join(result["各卦旺衰"]))
    if result.get("類象"):
        print("\n【七之三、類象（應在何人、何物、何處——取克體或生體之卦為主，餘卦為輔）】")
        for line in result["類象"]:
            print(f"  {line}")
    if result.get("應期"):
        print("\n【七之四、應期依據（擇一法並寫明）】")
        for k, v in result["應期"].items():
            print(f"  {k}：{v if isinstance(v, str) else '；'.join(v)}")

    if "爻位盤" in result:
        yp = result["爻位盤"]
        dong = ben['動爻位']
        print("\n【八、爻位盤（周易義理層・非原書步驟）】")
        for ln in reversed(yp["六爻"]):
            mark = "★" if ln["位"] == dong else "　"
            zhong = f"·{ln['得中']}" if ln["得中"] else ""
            ying = ("應↔" if ln["有應"] else "無應↔") + ln["應爻名稱"]
            cc = f"·{ln['承乘']}" if ln["承乘"] else ""
            print(f"  {mark}{ln['名稱']}（{ln['陰陽']}）：{ln['當位']}{zhong}·{ying}{cc}")
        if yp["二五中正相應"]:
            print("  ※ 二五中正相應——最強外援徵象")
        print(f"  → 動爻處境：{yp['動爻摘要']}")

    if "錯卦" in result:
        print(f"\n【九、錯卦／綜卦（參看）】 錯：{result['錯卦']['名稱']}　綜：{result['綜卦']['名稱']}")

    hex_num = ben['序號']
    if hex_num in HEXAGRAM_STRATEGY:
        s = get_hexagram_strategy(hex_num)
        print("\n【附錄・爻辭語氣參考（文本統計，非吉凶判決、非成功機率）】")
        print(f"  {ben['名稱']}：爻辭吉語比例 {s['ji_rate']}%・類型 {s['type']}・傳統標籤「{s['advice']}」")
        if s['change_path']:
            print(f"  語氣較吉的鄰卦：{s['change_path']}")
        print("  ※ 此表不看問事、不看體用旺衰；與上方判斷衝突時，以上方判斷為準。")

    print("\n" + "=" * 50)


_USAGE = """用法：
  python meihua_calc.py time [--at "YYYY-MM-DD HH:MM"] [--tz 8]   # 時間起卦（邵雍原法，預設）
  python meihua_calc.py time-precise [--at ...]                   # 分秒擴充法（非原法，用戶要求才用）
  python meihua_calc.py gregorian 2026 10 12 16 [分]               # 指定西曆時刻起卦
  python meihua_calc.py lunar 2026 9 3 16 [--leap]                 # 指定農曆日＋鐘點起卦
  python meihua_calc.py num 6 8 [9] [--at ...] [--add-hour]        # 數字起卦（占時只定卦氣）
  python meihua_calc.py gua 5 4 6 [--at ...]                       # 已算好上卦／下卦／動爻數，直接排卦
  python meihua_calc.py convert 2026 10 12                        # 西曆→農曆
  python meihua_calc.py pillars [--at ...]                         # 年月日時干支、月建

--at  起卦者當地鐘面時間；省略＝本機現在時間（雲端主機時區未必是用戶時區，務必帶 --at）
--tz  起卦者時區（小時，預設 8＝台灣/中國）；只影響節氣月建的判定
"""


def _pop_flag(args: List[str], name: str, has_value: bool = True):
    if name not in args:
        return None
    i = args.index(name)
    if has_value:
        val = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
        return val
    del args[i]
    return True


def main(argv: List[str]) -> None:
    args = list(argv[1:])
    at = _pop_flag(args, "--at")
    tz = float(_pop_flag(args, "--tz") or cal.DEFAULT_TZ_HOURS)
    leap = bool(_pop_flag(args, "--leap", has_value=False))
    add_hour = bool(_pop_flag(args, "--add-hour", has_value=False))
    cmd = args[0] if args else "time"
    rest = [int(x) for x in args[1:]] if cmd not in ("help", "-h", "--help") else []
    when = cal.parse_local(at)

    if cmd in ("time", "time-shichen"):
        result = qigua_by_gregorian_time(when.year, when.month, when.day, when.hour,
                                         when.minute, tz)
        print(f"\n起卦時間：{when:%Y-%m-%d %H:%M}（UTC{tz:+g}，邵雍年月日時法）"
              + ("" if at else "  ⚠ 取自本機時鐘"))
    elif cmd == "time-precise":
        result = qigua_by_gregorian_time_precise(when.year, when.month, when.day,
                                                 when.hour, when.minute, when.second, tz)
        print(f"\n起卦時間：{when:%Y-%m-%d %H:%M:%S}（分秒擴充法・非原法）")
    elif cmd == "gregorian" and len(rest) >= 4:
        minute = rest[4] if len(rest) > 4 else 0
        result = qigua_by_gregorian_time(rest[0], rest[1], rest[2], rest[3], minute, tz)
        print(f"\n起卦時間：西曆 {rest[0]}-{rest[1]:02d}-{rest[2]:02d} {rest[3]:02d}:{minute:02d}")
    elif cmd == "lunar" and len(rest) >= 4:
        result = qigua_by_time(rest[0], rest[1], rest[2], rest[3], leap, tz_hours=tz)
        print(f"\n起卦時間：農曆 {rest[0]}年{'閏' if leap else ''}{rest[1]}月{rest[2]}日 {rest[3]}時")
    elif cmd == "num" and len(rest) >= 2:
        result = qigua_by_numbers_at(when.year, when.month, when.day, when.hour,
                                     rest[0], rest[1], rest[2] if len(rest) > 2 else None,
                                     when.minute, add_hour, tz)
    elif cmd == "gua" and len(rest) >= 3:
        up, lo, dy = num_to_gua(rest[0]), num_to_gua(rest[1]), num_to_yao(rest[2])
        result = _analyze_hexagram(up, lo, dy, _shiling(when, tz) if at else None)
        result["計算過程"] = {"直接指定": f"上卦 {rest[0]}→{BAGUA[up]['name']}、下卦 {rest[1]}→{BAGUA[lo]['name']}、"
                                     f"動爻 {rest[2]}→{dy}（聲音／丈尺／物象等法手算後代入）"}
    elif cmd == "convert" and len(rest) >= 3:
        ly, lm, ld, is_leap = gregorian_to_lunar(rest[0], rest[1], rest[2])
        print(f"西曆: {rest[0]}年{rest[1]}月{rest[2]}日")
        print(f"農曆: {ly}年{'閏' if is_leap else ''}{lm}月{ld}日")
        return
    elif cmd == "pillars":
        p = cal.pillars(when, tz)
        print(f"{when:%Y-%m-%d %H:%M}（UTC{tz:+g}）年{p['年']} 月{p['月']} 日{p['日']} "
              f"時{p['時支']}　月建{p['月建']}（{p['時令']}）"
              + ("　⚠近交節" if p["近交節"] else "") + ("　（子時推日）" if p["子時推日"] else ""))
        return
    else:
        print(_USAGE)
        sys.exit(0 if cmd in ("help", "-h", "--help") else 1)
    print_result(result)


if __name__ == "__main__":
    configure_stdout()
    main(sys.argv)
