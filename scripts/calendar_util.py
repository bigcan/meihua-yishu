#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
曆法工具（無外部依賴）：節氣月建、日干支、年干支、時辰。

為什麼需要它
------------
- 卦氣旺衰（梅花）與月建（六爻）都以「節」換月：寅月始於立春、卯月始於驚蟄……
  用農曆月份近似會有最多約半個月的誤差，正好落在月初、月末的占卦就會判錯旺衰。
- 六爻的六獸、旬空、日沖日合都要「日干支」，讓使用者自己查容易查錯。

精度
----
太陽視黃經用 Meeus《Astronomical Algorithms》低精度公式（誤差約 0.01°，
約合 15 分鐘）。只有剛好在交節前後十幾分鐘內起卦才可能差一個月建，此時輸出會提示。
日干支以儒略日推算，屬純算術、無誤差。

時區
----
輸入一律是「起卦者當地的鐘面時間」加上時區（預設 UTC+8）。節氣時刻以 UTC 計算，
所以不論在台北、紐約起卦，月建都依真實天文時刻判定。
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

TIANGAN = "甲乙丙丁戊己庚辛壬癸"
DIZHI = "子丑寅卯辰巳午未申酉戌亥"
ZHI_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}
# 月建五行即其地支五行；辰戌丑未月土旺（《梅花易數》卦氣旺：坤艮旺於辰戌丑未月）
SEASON_OF_MONTH_ZHI = {
    "寅": "春", "卯": "春", "辰": "土月",
    "巳": "夏", "午": "夏", "未": "土月",
    "申": "秋", "酉": "秋", "戌": "土月",
    "亥": "冬", "子": "冬", "丑": "土月",
}
# 十二節（換月建的那一半節氣）與其太陽黃經
JIE_NAMES = {315: "立春", 345: "驚蟄", 15: "清明", 45: "立夏", 75: "芒種", 105: "小暑",
             135: "立秋", 165: "白露", 195: "寒露", 225: "立冬", 255: "大雪", 285: "小寒"}

DEFAULT_TZ_HOURS = 8.0


def _julian_day(dt_utc: datetime) -> float:
    """UTC datetime → 儒略日（JD）。"""
    y, m = dt_utc.year, dt_utc.month
    d = dt_utc.day + (dt_utc.hour + (dt_utc.minute + dt_utc.second / 60) / 60) / 24
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def sun_longitude(dt_utc: datetime) -> float:
    """太陽視黃經（度，0–360）。Meeus ch.25 低精度法，含 ΔT≈69s 修正。"""
    jd = _julian_day(dt_utc) + 69.0 / 86400.0
    t = (jd - 2451545.0) / 36525.0
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t * t
    m = math.radians(357.52911 + 35999.05029 * t - 0.0001537 * t * t)
    c = ((1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m)
         + (0.019993 - 0.000101 * t) * math.sin(2 * m)
         + 0.000289 * math.sin(3 * m))
    omega = math.radians(125.04 - 1934.136 * t)
    lam = l0 + c - 0.00569 - 0.00478 * math.sin(omega)
    return lam % 360.0


def to_utc(local: datetime, tz_hours: float = DEFAULT_TZ_HOURS) -> datetime:
    """鐘面時間（naive）→ UTC（naive）。若 local 已帶 tzinfo 則依其換算。"""
    if local.tzinfo is not None:
        return local.astimezone(timezone.utc).replace(tzinfo=None)
    return local - timedelta(hours=tz_hours)


def month_zhi(local: datetime, tz_hours: float = DEFAULT_TZ_HOURS) -> Tuple[str, float]:
    """依節氣定月建。回傳 (月支, 距最近交節的度數)。

    寅月始於立春（黃經 315°），每 30° 換一個月建。
    第二個值是與最近一個「節」的黃經距離（度），<0.02° 代表距交節約 30 分鐘內。
    """
    lon = sun_longitude(to_utc(local, tz_hours))
    idx = int(((lon - 315.0) % 360.0) // 30.0)  # 0=寅
    zhi = DIZHI[(idx + 2) % 12]
    off = (lon - 315.0) % 30.0
    return zhi, min(off, 30.0 - off)


def _jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def ganzhi_from_index(i: int) -> str:
    return TIANGAN[i % 10] + DIZHI[i % 12]


def day_ganzhi(local: datetime, zi_rollover: bool = True) -> Tuple[str, bool]:
    """日干支。zi_rollover=True 時 23:00 起已算次日（日始於子時，與梅花起卦一致）。

    回傳 (日干支, 是否因子時推日)。
    """
    d = local.date()
    rolled = False
    if zi_rollover and local.hour == 23:
        d = d + timedelta(days=1)
        rolled = True
    idx = (_jdn(d.year, d.month, d.day) + 49) % 60  # 2000-01-01 = 戊午
    return ganzhi_from_index(idx), rolled


def year_ganzhi_lichun(local: datetime, tz_hours: float = DEFAULT_TZ_HOURS) -> str:
    """年干支（以立春換年，六爻、八字用）。"""
    lon = sun_longitude(to_utc(local, tz_hours))
    y = local.year
    # 1–2 月太陽黃經約 280°–340°；尚未到立春（315°）→ 仍屬上一年
    if local.month <= 2 and not (315.0 <= lon < 345.0):
        y -= 1
    return ganzhi_from_index((y - 4) % 60)


def hour_zhi(hour: int) -> str:
    return DIZHI[((hour + 1) // 2) % 12]


def month_ganzhi(year_gz: str, m_zhi: str) -> str:
    """五虎遁：由年干定寅月天干。"""
    start = {"甲": 2, "己": 2, "乙": 4, "庚": 4, "丙": 6, "辛": 6,
             "丁": 8, "壬": 8, "戊": 0, "癸": 0}[year_gz[0]]  # 寅月天干：丙戊庚壬甲
    offset = (DIZHI.index(m_zhi) - 2) % 12
    return TIANGAN[(start + offset) % 10] + m_zhi


def pillars(local: datetime, tz_hours: float = DEFAULT_TZ_HOURS,
            zi_rollover: bool = True) -> Dict[str, object]:
    """一次取齊占卦需要的曆法資訊。"""
    m_zhi, dist = month_zhi(local, tz_hours)
    d_gz, rolled = day_ganzhi(local, zi_rollover)
    y_gz = year_ganzhi_lichun(local, tz_hours)
    return {
        "年": y_gz,
        "月": month_ganzhi(y_gz, m_zhi),
        "月建": m_zhi,
        "日": d_gz,
        "時支": hour_zhi(local.hour),
        "時令": SEASON_OF_MONTH_ZHI[m_zhi],
        "近交節": dist < 0.025,
        "子時推日": rolled,
    }


def parse_local(text: Optional[str]) -> datetime:
    """解析 'YYYY-MM-DD HH:MM[:SS]' 或 'now'（取系統鐘面時間）。"""
    if not text or text == "now":
        return datetime.now().replace(microsecond=0)
    text = text.strip().replace("T", " ").replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"無法解析時間：{text}（格式 YYYY-MM-DD HH:MM）")


if __name__ == "__main__":
    import sys
    when = parse_local(sys.argv[1] if len(sys.argv) > 1 else None)
    tz = float(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TZ_HOURS
    p = pillars(when, tz)
    print(f"{when}（UTC{tz:+g}）→ 年{p['年']} 月{p['月']} 日{p['日']} 時{p['時支']}  "
          f"月建{p['月建']}（{p['時令']}）{'  ⚠近交節' if p['近交節'] else ''}")
