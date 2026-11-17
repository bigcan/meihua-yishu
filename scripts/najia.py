#!/usr/bin/env python3
"""
納甲（六爻）裝卦與斷卦引擎
Najia (Liu Yao) Annotation & Judgement Engine

裝卦：納甲干支、八宮世應、六親、六獸、旬空、伏神。
斷卦依據（以《增刪卜易》《卜筮正宗》為準）：
- 每爻旺衰：月建（臨、扶、生、克、破、合）＋日辰（臨、扶、生、克、沖、合、墓）
- 日沖靜爻：旺相為「暗動」、休囚為「日破」（不可一律稱日破）
- 旬空：動空、旺空、有生扶者「不為空」，出旬／沖空即實；休囚靜空才是真空
- 動爻變化：回頭生、回頭克、化進、化退、化空、化破、化墓、化絕、化洩
- 用神兩現取捨、原神／忌神／仇神、動爻對用神的生克
- 六沖卦、六合卦、沖變合、合變沖、反吟、伏吟（依正確定義，只看動爻）
- 三合局：須有動爻參與
- 應期：依用神所處狀態（空、破、合、旺、衰、墓、動靜）給規則化建議

可獨立使用，亦可被 jinqian_gua.py 呼叫。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meihua_calc import (  # noqa: E402
    HEXAGRAMS,
    apply_change,
    binary_to_gua_pair,
    configure_stdout,
)
import calendar_util as cal  # noqa: E402

# ============================================================================
# 核心對照表
# ============================================================================

TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
ZHI_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

# 八純卦六爻納甲（自初爻到上爻）
PURE_GUA_NAJIA: Dict[int, List[str]] = {
    1: ["甲子", "甲寅", "甲辰", "壬午", "壬申", "壬戌"],  # 乾
    2: ["丁巳", "丁卯", "丁丑", "丁亥", "丁酉", "丁未"],  # 兌
    3: ["己卯", "己丑", "己亥", "己酉", "己未", "己巳"],  # 離
    4: ["庚子", "庚寅", "庚辰", "庚午", "庚申", "庚戌"],  # 震
    5: ["辛丑", "辛亥", "辛酉", "辛未", "辛巳", "辛卯"],  # 巽
    6: ["戊寅", "戊辰", "戊午", "戊申", "戊戌", "戊子"],  # 坎
    7: ["丙辰", "丙午", "丙申", "丙戌", "丙子", "丙寅"],  # 艮
    8: ["乙未", "乙巳", "乙卯", "癸丑", "癸亥", "癸酉"],  # 坤
}

PALACE_WUXING = {1: "金", 2: "金", 3: "火", 4: "木", 5: "木", 6: "水", 7: "土", 8: "土"}
PALACE_NAME = {1: "乾", 2: "兌", 3: "離", 4: "震", 5: "巽", 6: "坎", 7: "艮", 8: "坤"}

# 八宮卦序：本宮、一世、二世、三世、四世、五世、游魂、歸魂
PALACE_ORDER: Dict[int, List[int]] = {
    1: [1, 44, 33, 12, 20, 23, 35, 14],      # 乾宮
    2: [58, 47, 45, 31, 39, 15, 62, 54],     # 兌宮
    3: [30, 56, 50, 64, 4, 59, 6, 13],       # 離宮
    4: [51, 16, 40, 32, 46, 48, 28, 17],     # 震宮
    5: [57, 9, 37, 42, 25, 21, 27, 18],      # 巽宮
    6: [29, 60, 3, 63, 49, 55, 36, 7],       # 坎宮
    7: [52, 22, 26, 41, 38, 10, 61, 53],     # 艮宮
    8: [2, 24, 19, 11, 34, 43, 5, 8],        # 坤宮
}
HEX_TO_PALACE: Dict[int, Tuple[int, int]] = {}
for _palace, _seq in PALACE_ORDER.items():
    for _gen, _hex in enumerate(_seq):
        HEX_TO_PALACE[_hex] = (_palace, _gen)

SHI_POS = [6, 1, 2, 3, 4, 5, 4, 3]
YING_POS = [3, 4, 5, 6, 1, 2, 1, 6]
GENERATION_NAME = ["本宮", "一世", "二世", "三世", "四世", "五世", "游魂", "歸魂"]

WUXING_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WUXING_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

LIUSHOU_ORDER = ["青龍", "朱雀", "勾陳", "螣蛇", "白虎", "玄武"]
LIUSHOU_START = {"甲": 0, "乙": 0, "丙": 1, "丁": 1, "戊": 2, "己": 3,
                 "庚": 4, "辛": 4, "壬": 5, "癸": 5}

XUN_KONG = {
    "甲子": ["戌", "亥"], "甲戌": ["申", "酉"], "甲申": ["午", "未"],
    "甲午": ["辰", "巳"], "甲辰": ["寅", "卯"], "甲寅": ["子", "丑"],
}


def xunkong(day_ganzhi: str) -> List[str]:
    """日干支所在旬的空亡兩支。"""
    gi, zi = TIANGAN.index(day_ganzhi[0]), DIZHI.index(day_ganzhi[1])
    head_zhi = DIZHI[(zi - gi) % 12]
    return XUN_KONG["甲" + head_zhi]


# 向後相容：舊介面用的全表
GANZHI_TO_XUNKONG: Dict[str, List[str]] = {}
for _i in range(60):
    _gz = TIANGAN[_i % 10] + DIZHI[_i % 12]
    GANZHI_TO_XUNKONG[_gz] = xunkong(_gz)

LIU_CHONG = {
    "子": "午", "午": "子", "丑": "未", "未": "丑", "寅": "申", "申": "寅",
    "卯": "酉", "酉": "卯", "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳",
}
LIU_HE = {
    "子": "丑", "丑": "子", "寅": "亥", "亥": "寅", "卯": "戌", "戌": "卯",
    "辰": "酉", "酉": "辰", "巳": "申", "申": "巳", "午": "未", "未": "午",
}
SAN_HE = {
    ("申", "子", "辰"): "水", ("亥", "卯", "未"): "木",
    ("寅", "午", "戌"): "火", ("巳", "酉", "丑"): "金",
}

# 長生十二宮（《增刪卜易》：水土同長生於申）
CHANGSHENG = {"木": "亥", "火": "寅", "金": "巳", "水": "申", "土": "申"}
DIWANG = {"木": "卯", "火": "午", "金": "酉", "水": "子", "土": "子"}
MU = {"木": "未", "火": "戌", "金": "丑", "水": "辰", "土": "辰"}
JUE = {"木": "申", "火": "亥", "金": "寅", "水": "巳", "土": "巳"}

# 進神：同五行地支向前；退神：向後
JIN_SHEN = {("亥", "子"), ("寅", "卯"), ("巳", "午"), ("申", "酉"),
            ("丑", "辰"), ("辰", "未"), ("未", "戌"), ("戌", "丑")}
TUI_SHEN = {(b, a) for a, b in JIN_SHEN}

# 卦反吟：後天八卦方位相對之卦互變（乾巽、坎離、艮坤、震兌）
GUA_FANYIN = {frozenset({1, 5}), frozenset({6, 3}), frozenset({7, 8}), frozenset({4, 2})}

# 六沖卦（八純卦＋天雷无妄、雷天大壯）、六合卦
LIUCHONG_GUA = {1, 2, 29, 30, 51, 52, 57, 58, 25, 34}
LIUHE_GUA = {11, 12, 16, 24, 47, 56, 60, 22}

# 六親生克鏈：父母→兄弟→子孫→妻財→官鬼→父母
LIUQIN_SHENG = {"父母": "兄弟", "兄弟": "子孫", "子孫": "妻財", "妻財": "官鬼", "官鬼": "父母"}
LIUQIN_KE = {"父母": "子孫", "子孫": "官鬼", "官鬼": "兄弟", "兄弟": "妻財", "妻財": "父母"}

# 用神對照（問事 → 六親；「世」＝以世爻為用神，「應」＝以應爻為用神）
YONGSHEN_MAP = {
    # 自己
    "自身": "世", "自己": "世", "運勢": "世", "平安": "世", "出行": "世", "遷居": "世",
    # 他人（無親屬關係的對方）
    "對方": "應", "他人": "應", "對手": "應", "合作方": "應", "陌生人": "應",
    # 兄弟
    "兄弟": "兄弟", "姐妹": "兄弟", "朋友": "兄弟", "同事": "兄弟", "同學": "兄弟",
    "夥伴": "兄弟", "競爭者": "兄弟",
    # 父母
    "父母": "父母", "長輩": "父母", "師長": "父母", "老師": "父母",
    "房屋": "父母", "房子": "父母", "車輛": "父母", "船車": "父母", "文書": "父母",
    "契約": "父母", "合約": "父母", "學業": "父母", "考試成績": "父母",
    "證件": "父母", "簽證": "父母", "信件": "父母", "消息": "父母", "論文": "父母",
    # 子孫
    "子女": "子孫", "孩子": "子孫", "懷孕": "子孫", "晚輩": "子孫", "學生": "子孫",
    "寵物": "子孫", "六畜": "子孫", "藥物": "子孫", "醫藥": "子孫", "醫生": "子孫",
    "僧道": "子孫", "解憂": "子孫", "避禍": "子孫",
    # 妻財
    "妻子": "妻財", "女友": "妻財", "情人（女）": "妻財", "下屬": "妻財", "員工": "妻財",
    "財物": "妻財", "錢財": "妻財", "求財": "妻財", "薪資": "妻財", "加薪": "妻財", "收入": "妻財", "獎金": "妻財",
    "買賣": "妻財", "生意": "妻財", "投資": "妻財", "貨物": "妻財", "物品": "妻財",
    "失物": "妻財", "價格": "妻財",
    # 官鬼
    "丈夫": "官鬼", "男友": "官鬼", "情人（男）": "官鬼", "工作": "官鬼", "事業": "官鬼",
    "求職": "官鬼", "官位": "官鬼", "功名": "官鬼", "考試": "官鬼", "升遷": "官鬼",
    "上司": "官鬼", "官府": "官鬼", "疾病": "官鬼", "病況": "官鬼", "災禍": "官鬼",
    "鬼神": "官鬼", "盜賊": "官鬼", "訴訟": "官鬼", "官司": "官鬼",
}

# 需先釐清的問事：回傳提示而非亂取用神
AMBIGUOUS_ASKS = {
    "婚姻": "男問妻子／女友用「妻財」，女問丈夫／男友用「官鬼」；問自己姻緣運用「自身」（世爻）。請改用 --ask 妻子／女友／丈夫／男友。",
    "感情": "同「婚姻」：男問用 女友（妻財）、女問用 男友（官鬼）。",
    "健康": "問自己身體用「自身」（世爻，兼看官鬼）；問家人依其六親（父母／子女…）；問病情本身用「疾病」。",
    "工作": None,
}

YONGSHEN_NOTES = {
    "疾病": "問病況看官鬼；問病人安危則以病人本身之用神（自己＝世、父＝父母、子＝子孫…）為主，"
           "官鬼旺動克用神為凶，子孫（醫藥）動為解。",
    "考試": "問能否考上看官鬼（功名）；問分數、文章好壞看父母。官父相生為上。",
    "出行": "問自身出行平安以世爻為用；子孫持世或動為平安，官鬼持世動為阻。",
    "加薪": "加薪重在錢，用妻財；若重點是職級晉升，改用「升遷」（官鬼）。兼看官鬼（公司／主管）是否生世。",
    "失物": "以妻財為用神；財爻在內卦、靜，物在家中；在外卦或動則已外流。",
}


def liuqin_from(palace_wuxing: str, yao_wuxing: str) -> str:
    """同我＝兄弟、生我＝父母、我生＝子孫、克我＝官鬼、我克＝妻財"""
    if yao_wuxing == palace_wuxing:
        return "兄弟"
    if WUXING_SHENG[yao_wuxing] == palace_wuxing:
        return "父母"
    if WUXING_SHENG[palace_wuxing] == yao_wuxing:
        return "子孫"
    if WUXING_KE[yao_wuxing] == palace_wuxing:
        return "官鬼"
    return "妻財"


def wx_relation(src: str, dst: str) -> str:
    """src 五行對 dst 五行的作用：生、克、扶（同）、洩（dst 生 src）、耗（dst 克 src）。"""
    if src == dst:
        return "扶"
    if WUXING_SHENG[src] == dst:
        return "生"
    if WUXING_KE[src] == dst:
        return "克"
    if WUXING_SHENG[dst] == src:
        return "洩"
    return "耗"


def hex_najia(upper: int, lower: int) -> List[str]:
    """下三爻取下卦純卦之下三爻，上三爻取上卦純卦之上三爻。"""
    return PURE_GUA_NAJIA[lower][:3] + PURE_GUA_NAJIA[upper][3:]


# ============================================================================
# 資料結構
# ============================================================================

@dataclass
class YaoNajia:
    position: int
    is_yang: bool
    gan: str
    zhi: str
    wuxing: str
    liuqin: str
    liushou: Optional[str] = None
    is_shi: bool = False
    is_ying: bool = False
    is_changing: bool = False
    bian_gan: Optional[str] = None
    bian_zhi: Optional[str] = None
    bian_wuxing: Optional[str] = None
    bian_liuqin: Optional[str] = None
    # 旺衰
    month_rel: str = ""          # 臨月/月扶/月生/月克/月破/月合/洩/耗
    day_rel: str = ""            # 臨日/日扶/日生/日克/日沖/日合/日墓/…
    strength: int = 0            # 綜合力量分
    state: str = ""              # 旺相/平/休囚
    is_void: bool = False        # 逢旬空（不論真假）
    void_kind: str = ""          # 真空／不為空（理由）
    is_yue_po: bool = False      # 月破
    is_ri_po: bool = False       # 日破（休囚靜爻被日沖）
    is_an_dong: bool = False     # 暗動（旺相靜爻被日沖）
    is_ri_chong: bool = False    # 被日沖（原始事實）
    is_yue_chong: bool = False   # 同 is_yue_po（向後相容）
    is_ri_he: bool = False
    is_ri_mu: bool = False       # 入日墓
    change_notes: List[str] = field(default_factory=list)  # 動變（回頭生克、化進退…）
    note: List[str] = field(default_factory=list)

    def ganzhi(self) -> str:
        return self.gan + self.zhi

    @property
    def active(self) -> bool:
        """能生克他爻者：明動或暗動。"""
        return self.is_changing or self.is_an_dong


@dataclass
class AnnotatedHexagram:
    upper: int
    lower: int
    hex_num: int
    hex_name: str
    palace: int
    palace_name: str
    generation: int
    generation_name: str
    palace_wuxing: str
    shi_pos: int
    ying_pos: int
    yaos: List[YaoNajia]
    bian_upper: Optional[int] = None
    bian_lower: Optional[int] = None
    bian_hex_num: Optional[int] = None
    bian_hex_name: Optional[str] = None
    bian_palace: Optional[int] = None
    bian_palace_name: Optional[str] = None
    day_ganzhi: Optional[str] = None
    month_zhi: Optional[str] = None
    void_zhis: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    sanhe: List[Tuple[str, List[int]]] = field(default_factory=list)  # (局五行, 參與之爻位)

    def shi(self) -> YaoNajia:
        return self.yaos[self.shi_pos - 1]

    def ying(self) -> YaoNajia:
        return self.yaos[self.ying_pos - 1]


# ============================================================================
# 旺衰
# ============================================================================

def _month_relation(wx: str, zhi: str, month_zhi: str) -> Tuple[str, int]:
    if zhi == month_zhi:
        return "臨月建", 3
    if LIU_CHONG[zhi] == month_zhi:
        return "月破", -3
    rel = wx_relation(ZHI_WUXING[month_zhi], wx)  # 月對爻
    label = {"扶": "月扶", "生": "月生", "克": "月克", "洩": "洩於月建（爻去生月）", "耗": "耗於月建（爻去克月）"}[rel]
    score = {"扶": 2, "生": 2, "克": -2, "洩": -1, "耗": -1}[rel]
    if LIU_HE[zhi] == month_zhi and score <= 0:
        label += "・月合"
        score += 1
    return label, score


def _day_relation(wx: str, zhi: str, day_zhi: str) -> Tuple[str, int, bool, bool]:
    """回傳 (標籤, 分數, 是否被日沖, 是否入日墓)。日沖之最終判讀（暗動/日破）在外層依旺衰決定。"""
    if zhi == day_zhi:
        return "臨日辰", 3, False, False
    if LIU_CHONG[zhi] == day_zhi:
        return "日沖", 0, True, False
    if MU[wx] == day_zhi:
        return "入日墓", -1, False, True
    rel = wx_relation(ZHI_WUXING[day_zhi], wx)
    label = {"扶": "日扶", "生": "日生", "克": "日克", "洩": "洩於日辰（爻去生日）", "耗": "耗於日辰（爻去克日）"}[rel]
    score = {"扶": 2, "生": 2, "克": -2, "洩": -1, "耗": 0}[rel]
    if LIU_HE[zhi] == day_zhi:
        label += "・日合"
        score += 1
    if DIWANG[wx] == day_zhi and rel != "扶":
        score += 1
    return label, score, False, False


def _state_label(score: int) -> str:
    if score >= 2:
        return "旺相"
    if score >= 0:
        return "平"
    return "休囚"


def _change_notes(y: YaoNajia, month_zhi: Optional[str], void_zhis: List[str]) -> None:
    """動爻化出之變爻對本爻的作用。"""
    if not y.is_changing or not y.bian_zhi:
        return
    b_wx = y.bian_wuxing
    pair = (y.zhi, y.bian_zhi)
    if pair in JIN_SHEN:
        y.change_notes.append("化進神（力量增長、事向前推進）")
    elif pair in TUI_SHEN:
        y.change_notes.append("化退神（力量消退、事情退縮）")
    elif y.zhi == y.bian_zhi:
        y.change_notes.append("動而不變（爻伏吟：呻吟、停滯）")
    else:
        rel = wx_relation(b_wx, y.wuxing)
        if LIU_CHONG[y.zhi] == y.bian_zhi:
            y.change_notes.append("化回頭沖（爻反吟：反覆、動搖）")
        if rel == "生":
            y.change_notes.append("化回頭生（得助，大吉之變）")
        elif rel == "克":
            y.change_notes.append("化回頭克（自敗，凶）")
        elif rel == "洩":
            y.change_notes.append("化洩（力量外流、減力）")
        elif rel == "耗":
            y.change_notes.append("化耗（我克變爻，費力）")
        if LIU_HE[y.zhi] == y.bian_zhi:
            y.change_notes.append("化合（動而被合絆，待沖而發）")
    if y.bian_zhi == MU[y.wuxing]:
        y.change_notes.append("化墓（受困、不能自主）")
    if y.bian_zhi == JUE[y.wuxing]:
        y.change_notes.append("化絕（力竭，須有生扶方解）")
    if y.bian_zhi in void_zhis:
        y.change_notes.append("化空（變爻旬空：事有始無終，出空可應）")
    if month_zhi and LIU_CHONG[y.bian_zhi] == month_zhi:
        y.change_notes.append("化破（變爻月破：根基不穩）")


# ============================================================================
# 主要 API
# ============================================================================

def annotate(
    binary: str,
    changing: Optional[List[int]] = None,
    day_ganzhi: Optional[str] = None,
    month_zhi: Optional[str] = None,
) -> AnnotatedHexagram:
    """
    完整裝卦＋旺衰標註。

    binary: 6 字元 0/1，最左為上爻、最右為初爻（與 meihua_calc 一致）
    changing: 動爻位置（1..6，自下而上）
    day_ganzhi: 日干支（例 "甲子"）；六獸、旬空、日辰旺衰
    month_zhi: 月建（以節氣為準，例 "寅"）；月令旺衰、月破
    """
    changing = sorted(set(changing or []))
    upper, lower = binary_to_gua_pair(binary)
    hex_num, hex_name = HEXAGRAMS[(upper, lower)]
    palace, generation = HEX_TO_PALACE[hex_num]
    palace_wuxing = PALACE_WUXING[palace]
    shi, ying = SHI_POS[generation], YING_POS[generation]

    nj = hex_najia(upper, lower)
    yaos: List[YaoNajia] = []
    for i in range(6):
        position = i + 1
        gan, zhi = nj[i][0], nj[i][1]
        wx = ZHI_WUXING[zhi]
        yaos.append(YaoNajia(
            position=position, is_yang=binary[6 - position] == "1",
            gan=gan, zhi=zhi, wuxing=wx, liuqin=liuqin_from(palace_wuxing, wx),
            is_shi=position == shi, is_ying=position == ying,
            is_changing=position in changing,
        ))

    h = AnnotatedHexagram(
        upper=upper, lower=lower, hex_num=hex_num, hex_name=hex_name,
        palace=palace, palace_name=PALACE_NAME[palace],
        generation=generation, generation_name=GENERATION_NAME[generation],
        palace_wuxing=palace_wuxing, shi_pos=shi, ying_pos=ying, yaos=yaos,
        day_ganzhi=day_ganzhi, month_zhi=month_zhi,
    )

    if changing:
        bian_bin = binary
        for p in changing:
            bian_bin = apply_change(bian_bin, p)
        h.bian_upper, h.bian_lower = binary_to_gua_pair(bian_bin)
        h.bian_hex_num, h.bian_hex_name = HEXAGRAMS[(h.bian_upper, h.bian_lower)]
        h.bian_palace = HEX_TO_PALACE[h.bian_hex_num][0]
        h.bian_palace_name = PALACE_NAME[h.bian_palace]
        bian_nj = hex_najia(h.bian_upper, h.bian_lower)
        for y in yaos:
            if y.is_changing:
                y.bian_gan, y.bian_zhi = bian_nj[y.position - 1][0], bian_nj[y.position - 1][1]
                y.bian_wuxing = ZHI_WUXING[y.bian_zhi]
                # 變爻六親仍以本卦之宮五行論
                y.bian_liuqin = liuqin_from(palace_wuxing, y.bian_wuxing)

    if day_ganzhi:
        start = LIUSHOU_START.get(day_ganzhi[0])
        if start is not None:
            for i, y in enumerate(yaos):
                y.liushou = LIUSHOU_ORDER[(start + i) % 6]
        h.void_zhis = xunkong(day_ganzhi)

    # 旺衰
    for y in yaos:
        score = 0
        if month_zhi:
            y.month_rel, ms = _month_relation(y.wuxing, y.zhi, month_zhi)
            score += ms
            y.is_yue_po = y.is_yue_chong = y.month_rel == "月破"
        if day_ganzhi:
            dz = day_ganzhi[1]
            y.day_rel, ds, chong, mu = _day_relation(y.wuxing, y.zhi, dz)
            y.is_ri_chong, y.is_ri_mu = chong, mu
            y.is_ri_he = LIU_HE[y.zhi] == dz
            score += ds
        y.strength = score
        y.state = _state_label(score) if (month_zhi or day_ganzhi) else ""

        # 日沖：靜爻旺相＝暗動；休囚＝日破；動爻逢日沖＝沖散（休囚）或沖起（旺）
        if y.is_ri_chong:
            month_ok = month_zhi is None or _month_relation(y.wuxing, y.zhi, month_zhi)[1] > 0
            if not y.is_changing:
                if month_ok:
                    y.is_an_dong = True
                    y.day_rel = ("日沖・沖空則實（沖起）" if y.zhi in h.void_zhis else "日沖・暗動")
                else:
                    y.is_ri_po = True
                    y.day_rel = "日沖・日破"
                    y.strength -= 2
            else:
                y.day_rel = "日沖・動而逢沖" + ("（旺不為散）" if month_ok else "（衰則沖散）")
                if not month_ok:
                    y.strength -= 2
            y.state = _state_label(y.strength)

        # 旬空真假
        if y.zhi in h.void_zhis:
            y.is_void = True
            reasons = []
            if y.is_changing:
                reasons.append("動")
            if y.state == "旺相":
                reasons.append("旺")
            if y.is_ri_chong:
                reasons.append("沖空則實")
            if reasons:
                y.void_kind = f"不為真空（{'・'.join(reasons)}）：暫時未到，出旬或沖空時有力"
            elif y.is_yue_po:
                y.void_kind = "真空又月破：此爻無用"
            else:
                y.void_kind = "真空（休囚靜空）：到底落空，除非出旬後得生扶"

        _change_notes(y, month_zhi, h.void_zhis)

    _detect_gua_patterns(h)
    _detect_sanhe(h)
    return h


def _detect_gua_patterns(h: AnnotatedHexagram) -> None:
    if h.hex_num in LIUCHONG_GUA:
        h.notes.append("本卦為六沖卦：事散、不久、近事速決；問久遠或合和之事不利")
    if h.hex_num in LIUHE_GUA:
        h.notes.append("本卦為六合卦：事聚、和合、可成；問解散、脫身之事反慢")
    if h.bian_hex_num:
        if h.hex_num in LIUHE_GUA and h.bian_hex_num in LIUCHONG_GUA:
            h.notes.append("合變沖：先合後散、有始無終")
        if h.hex_num in LIUCHONG_GUA and h.bian_hex_num in LIUHE_GUA:
            h.notes.append("沖變合：先散後聚、先難後成")
        if h.bian_hex_num in LIUCHONG_GUA and h.hex_num not in LIUCHONG_GUA:
            h.notes.append("變卦為六沖卦：結局趨散")

        # 伏吟／反吟：只看動了的三爻卦。內卦或外卦變動後地支全同＝伏吟；全沖＝反吟。
        bian_nj = hex_najia(h.bian_upper, h.bian_lower)  # type: ignore[arg-type]
        for name, rng, ben_g, bian_g in (("內卦", range(0, 3), h.lower, h.bian_lower),
                                         ("外卦", range(3, 6), h.upper, h.bian_upper)):
            if ben_g == bian_g:
                continue
            zs = [h.yaos[i].zhi for i in rng]
            bzs = [bian_nj[i][1] for i in rng]
            if zs == bzs:
                h.notes.append(f"{name}伏吟（乾震互變，地支不變）：憂鬱呻吟、欲動不能")
            elif all(LIU_CHONG[a] == b for a, b in zip(zs, bzs)):
                h.notes.append(f"{name}爻反吟（變爻地支逐一相沖）：反覆不定、得而復失")
            elif frozenset({ben_g, bian_g}) in GUA_FANYIN:
                h.notes.append(f"{name}卦反吟（{PALACE_NAME[ben_g]}變{PALACE_NAME[bian_g]}，後天方位相對）：事情往返、反覆")


def _detect_sanhe(h: AnnotatedHexagram) -> None:
    """三合局：三支齊備且至少兩支來自動爻／變爻（一動二靜不成局）。日月可補一支。"""
    for combo, wx in SAN_HE.items():
        sources: Dict[str, List[str]] = {z: [] for z in combo}
        for y in h.yaos:
            if y.zhi in combo:
                sources[y.zhi].append(f"{y.position}爻{'動' if y.is_changing else '靜'}")
            if y.is_changing and y.bian_zhi in combo:
                sources[y.bian_zhi].append(f"{y.position}爻變")
        if h.day_ganzhi and h.day_ganzhi[1] in combo:
            sources[h.day_ganzhi[1]].append("日")
        if h.month_zhi and h.month_zhi in combo:
            sources[h.month_zhi].append("月")
        if not all(sources.values()):
            continue
        # 每支取一個來源，至少兩支由「不同的」動爻（或其變爻）提供
        active_pos = [{int(s_.split("爻")[0]) for s_ in sources[z] if "動" in s_ or "變" in s_}
                      for z in combo]
        chosen: set = set()
        for opts in sorted(active_pos, key=len):
            free = opts - chosen
            if free:
                chosen.add(min(free))
        if len(chosen) >= 2:
            h.sanhe.append((wx, sorted({y.position for y in h.yaos
                                        if y.zhi in combo or (y.is_changing and y.bian_zhi in combo)})))
            desc = "、".join(f"{z}({'/'.join(sources[z])})" for z in combo)
            h.notes.append(f"三合{wx}局成：{desc}——{wx}之六親（{liuqin_from(h.palace_wuxing, wx)}）力量大增")


# ============================================================================
# 用神／原神／忌神
# ============================================================================

def _rank_yongshen(y: YaoNajia) -> Tuple:
    """用神兩現取捨：捨靜取動、捨空取不空、捨破取不破、捨衰取旺、持世者優先。"""
    return (
        y.is_changing or y.is_an_dong,
        not (y.void_kind.startswith("真空")),
        not (y.is_yue_po or y.is_ri_po),
        y.is_shi or y.is_ying,
        y.strength,
    )


def _effects_on(h: AnnotatedHexagram, target: YaoNajia) -> List[Tuple[str, int]]:
    """明動、暗動之爻對 target 的生克。回傳 (說明, 分數)。

    休囚之爻動仍能生克，但力減半；被回頭克或月破者生克無力；
    參與三合局者，其五行已化入局中，個別生克改由局論。
    """
    in_ju = {p for _, ps in h.sanhe for p in ps}
    out: List[Tuple[str, int]] = []
    for y in h.yaos:
        if y is target or not y.active:
            continue
        rel = wx_relation(y.wuxing, target.wuxing)
        if rel not in ("生", "克"):
            continue
        tag = "動" if y.is_changing else "暗動"
        base = 2 if rel == "生" else -2
        if y.position in in_ju:
            out.append((f"{y.position}爻{y.liuqin}{y.zhi}{tag}{rel}用神，但已入三合局，改依局論", 0))
            continue
        if any("回頭克" in n for n in y.change_notes) or y.is_yue_po or y.is_ri_po:
            out.append((f"{y.position}爻{y.liuqin}{y.zhi}{y.wuxing}{tag}→{rel}用神（自身受制，生克無力）", 0))
        elif y.state == "休囚":
            out.append((f"{y.position}爻{y.liuqin}{y.zhi}{y.wuxing}{tag}→{rel}用神（自身休囚，力減半）", base // 2))
        else:
            out.append((f"{y.position}爻{y.liuqin}{y.zhi}{y.wuxing}{tag}→{rel}用神", base))
    for wx, ps in h.sanhe:
        rel = wx_relation(wx, target.wuxing)
        score = {"生": 3, "扶": 2, "克": -3}.get(rel, 0)
        if score:
            out.append((f"三合{wx}局（{'、'.join(map(str, ps))}爻）{'生' if rel == '生' else ('扶' if rel == '扶' else '克')}用神", score))
    return out


def find_yongshen(h: AnnotatedHexagram, question_type: str) -> Dict:
    """依問事類型定用神，並整理原神／忌神／仇神與動爻作用。"""
    if AMBIGUOUS_ASKS.get(question_type):
        return {"error": f"「{question_type}」需先釐清：{AMBIGUOUS_ASKS[question_type]}"}
    if question_type not in YONGSHEN_MAP:
        return {"error": f"未知問事類型：{question_type}。可用：python najia.py list-questions"}
    target = YONGSHEN_MAP[question_type]
    result: Dict = {"question_type": question_type, "note": YONGSHEN_NOTES.get(question_type)}

    if target == "世":
        primary = h.shi()
        result.update(liuqin=f"世爻（{primary.liuqin}）", target_liuqin=primary.liuqin,
                      yaos=[primary], fushen=None, primary=primary)
    elif target == "應":
        primary = h.ying()
        result.update(liuqin=f"應爻（{primary.liuqin}）", target_liuqin=primary.liuqin,
                      yaos=[primary], fushen=None, primary=primary)
    else:
        matches = [y for y in h.yaos if y.liuqin == target]
        primary = max(matches, key=_rank_yongshen) if matches else None
        result.update(liuqin=target, target_liuqin=target, yaos=matches, primary=primary,
                      fushen=None if matches else _find_fushen(h, target))
        # 變爻化出用神
        result["bian_yongshen"] = [y for y in h.yaos if y.is_changing and y.bian_liuqin == target]

    t = result["target_liuqin"]
    yuan = [k for k, v in LIUQIN_SHENG.items() if v == t][0]
    ji = [k for k, v in LIUQIN_KE.items() if v == t][0]
    chou = [k for k, v in LIUQIN_KE.items() if v == yuan][0]
    result["yuanshen"] = (yuan, [y for y in h.yaos if y.liuqin == yuan])
    result["jishen"] = (ji, [y for y in h.yaos if y.liuqin == ji])
    result["choushen"] = (chou, [y for y in h.yaos if y.liuqin == chou])
    if result.get("primary"):
        result["effects"] = _effects_on(h, result["primary"])
        result["verdict"] = _verdict(h, result)
    return result


def _find_fushen(h: AnnotatedHexagram, target_liuqin: str) -> Optional[Dict]:
    """用神不上卦：取本宮首卦（八純卦）同位之爻為伏神，其上本卦之爻為飛神。"""
    for i, gz in enumerate(PURE_GUA_NAJIA[h.palace]):
        wx = ZHI_WUXING[gz[1]]
        if liuqin_from(h.palace_wuxing, wx) != target_liuqin:
            continue
        fei = h.yaos[i]
        rel = wx_relation(fei.wuxing, wx)
        fei_note = {"生": "飛來生伏（得長生，伏神有用）", "扶": "飛伏比和（伏神得扶）",
                    "克": "飛來克伏（伏神受制，難出）", "洩": "伏去生飛（洩氣）",
                    "耗": "伏去克飛（伏神尚能出）"}[rel]
        state = ""
        if h.month_zhi and h.day_ganzhi:
            ml, ms = _month_relation(wx, gz[1], h.month_zhi)
            dl, ds, _, _ = _day_relation(wx, gz[1], h.day_ganzhi[1])
            state = f"{_state_label(ms + ds)}：{ml}、{dl}"
            if gz[1] in h.void_zhis:
                state += "、旬空"
        return {"position": i + 1, "ganzhi": gz, "wuxing": wx, "liuqin": target_liuqin,
                "fei_yao": f"{fei.ganzhi()}（{fei.liuqin}）", "fei_rel": fei_note, "state": state,
                "note": "伏神旺相、得日月生扶或飛神生之，可提拔出用；休囚又被飛神克，所求難得。"}
    return None


def _verdict(h: AnnotatedHexagram, r: Dict) -> Dict:
    """把用神狀態與動爻作用整理成方向性結論（供解讀起點，非機械判決）。"""
    y: YaoNajia = r["primary"]
    score = y.strength
    reasons = [f"用神 {y.position}爻{y.liuqin}{y.ganzhi()}：{y.month_rel or '月建未知'}、{y.day_rel or '日辰未知'} → {y.state or '旺衰未知'}"]
    if y.void_kind.startswith("真空"):
        score -= 3
        reasons.append("用神真空")
    if y.is_yue_po:
        reasons.append("用神月破（出月或填實之時方有轉機）")
    for n in y.change_notes:
        if "回頭生" in n or "進神" in n:
            score += 2
        if "回頭克" in n or "化破" in n or "化絕" in n:
            score -= 2
        if "退神" in n or "化墓" in n or "化空" in n:
            score -= 1
        reasons.append(f"用神{n}")
    for e, s_ in r.get("effects", []):
        score += s_
        reasons.append(e)
    # 貪生忘克：忌神動而原神亦動，忌生原、原生用，反成助力
    yuan_active = [x for x in r["yuanshen"][1] if x.active]
    ji_active = [x for x in r["jishen"][1] if x.active]
    yuan_ok = [x for x in yuan_active if not (x.is_yue_po or x.void_kind.startswith("真空")
                                              or any("回頭克" in n for n in x.change_notes))]
    if ji_active and yuan_ok:
        score += 2
        reasons.append("忌神、原神同動：忌生原、原生用（貪生忘克），忌神反為助力")
    shi = h.shi()
    if y is not shi:
        rel = wx_relation(y.wuxing, shi.wuxing)
        if rel in ("生", "扶"):
            reasons.append(f"用神{rel}世（所求之事來就我）")
            score += 1
        elif rel == "克" and r["target_liuqin"] in ("妻財",):
            reasons.append("財克世（財來就我）")
            score += 1
        elif rel == "克":
            reasons.append("用神克世（事來逼我，或成而有壓力）")
    if score >= 4:
        label = "有利：用神有力，所問之事傾向可成"
    elif score >= 1:
        label = "小利：用神尚可，事可望而需努力或待時"
    elif score >= -1:
        label = "未定：吉凶參半，關鍵在應期與人為"
    elif score >= -4:
        label = "不利：用神受制，事多阻礙，宜調整或延後"
    else:
        label = "大不利：用神無氣又受克，此事難成"
    return {"score": score, "label": label, "reasons": reasons}


# ============================================================================
# 應期
# ============================================================================

def suggest_yingqi(h: AnnotatedHexagram, y: Optional[YaoNajia]) -> List[str]:
    """《增刪卜易・應期章》規則化：依用神狀態給候選應期（以日／月地支表示）。"""
    if not y:
        return ["用神不上卦：以伏神地支值日、或沖開飛神之日為期；伏神休囚則所求難成。"]
    tips: List[str] = []
    z, wx = y.zhi, y.wuxing
    if y.is_void:
        tips.append(f"旬空：出旬後逢{z}日（填實）或{LIU_CHONG[z]}日（沖空）應")
    if y.is_yue_po:
        tips.append(f"月破：出月後，逢{z}日／月（填實）或{LIU_HE[z]}日（合破）應")
    if y.is_ri_po:
        tips.append(f"日破：逢{z}日填實或得生扶之日")
    if y.is_ri_he or any("化合" in n for n in y.change_notes):
        tips.append(f"逢合被絆：待{LIU_CHONG[z]}日沖開而應")
    if y.is_ri_mu or any("化墓" in n for n in y.change_notes):
        tips.append(f"入墓：逢{LIU_CHONG[MU[wx]]}日沖墓而出")
    if y.is_changing and not y.is_void:
        tips.append(f"用神動：逢{z}日（值日）或{LIU_HE[z]}日（合住）應")
    if not y.is_changing and not y.is_void and not y.is_yue_po:
        if y.state == "旺相":
            tips.append(f"靜而旺：逢{LIU_CHONG[z]}日沖起而應（靜待沖）")
        else:
            tips.append(f"靜而衰：逢生扶之日（{CHANGSHENG[wx]}長生、{wx}旺日）方應")
    if y.strength >= 6:
        tips.append(f"太旺：逢{MU[wx]}日（墓庫收之）應")
    tips.append("近事應日、遠事應月；問年內之事可把上列地支換成月份")
    return tips


# ============================================================================
# 輸出
# ============================================================================

def _yao_line(y: YaoNajia) -> str:
    if y.is_yang and y.is_changing:
        return "▅▅▅ O"
    if y.is_yang:
        return "▅▅▅  "
    if y.is_changing:
        return "▅ ▅ X"
    return "▅ ▅  "


def print_hexagram(h: AnnotatedHexagram) -> None:
    print("\n" + "=" * 64)
    print(f"📜 納甲裝卦：第{h.hex_num}卦 {h.hex_name}　{h.palace_name}宮{h.generation_name}卦（宮五行{h.palace_wuxing}）")
    if h.bian_hex_num:
        print(f"   變卦：第{h.bian_hex_num}卦 {h.bian_hex_name}（{h.bian_palace_name}宮）")
    line = []
    if h.month_zhi:
        line.append(f"月建 {h.month_zhi}")
    if h.day_ganzhi:
        line.append(f"日辰 {h.day_ganzhi}　旬空 {'、'.join(h.void_zhis)}")
    if line:
        print("   " + "　".join(line))
    else:
        print("   ⚠ 未提供月建、日辰：旺衰、旬空、日沖月破皆無法判斷，斷卦精度大減")
    print("=" * 64)
    print(f"{'六獸':<3} {'六親':<3} {'干支五行':<6} {'爻':<6} {'世應':<2} {'變爻':<10} {'旺衰'}")
    print("-" * 64)
    for y in reversed(h.yaos):
        mark = "世" if y.is_shi else ("應" if y.is_ying else "  ")
        bian = f"→{y.bian_gan}{y.bian_zhi}{y.bian_wuxing}{y.bian_liuqin}" if y.is_changing else ""
        flags = []
        if y.month_rel or y.day_rel:
            flags.append(f"{y.state}（{y.month_rel}／{y.day_rel}）")
        if y.is_void:
            flags.append("空")
        print(f"{(y.liushou or ''):<3} {y.liuqin:<3} {y.ganzhi()}{y.wuxing:<4} {_yao_line(y):<6} {mark:<2} {bian:<10} {' '.join(flags)}")
    details = []
    for y in reversed(h.yaos):
        items = []
        if y.void_kind:
            items.append(y.void_kind)
        items.extend(y.change_notes)
        if items:
            details.append(f"  {y.position}爻{y.liuqin}{y.zhi}：" + "；".join(items))
    if details:
        print("\n【爻象細節】")
        print("\n".join(details))
    if h.notes:
        print("\n【卦象格局】")
        for n in h.notes:
            print(f"  • {n}")
    shi, ying = h.shi(), h.ying()
    rel = wx_relation(ying.wuxing, shi.wuxing)
    rel_txt = {"生": "應生世（對方助我）", "克": "應克世（對方壓我）", "扶": "世應比和（彼此對等）",
               "洩": "世生應（我付出給對方）", "耗": "世克應（我能制對方）"}[rel]
    acts = [f"{y.position}爻{y.liuqin}{y.zhi}{'動' if y.is_changing else '暗動'}{wx_relation(y.wuxing, shi.wuxing)}世"
            for y in h.yaos if y.active and y is not shi and wx_relation(y.wuxing, shi.wuxing) in ("生", "克")]
    if acts:
        print("\n【動爻對世爻】" + "；".join(acts))
    print(f"\n【世應】世 {shi.position}爻{shi.liuqin}{shi.zhi}（{shi.state or '—'}）"
          f"／應 {ying.position}爻{ying.liuqin}{ying.zhi}（{ying.state or '—'}）：{rel_txt}")


def print_yongshen(h: AnnotatedHexagram, r: Dict) -> None:
    print("\n【用神】")
    if "error" in r:
        print(f"  {r['error']}")
        return
    print(f"  問事：{r['question_type']} → 用神「{r['liuqin']}」")
    if r.get("note"):
        print(f"  註：{r['note']}")
    y = r.get("primary")
    if y:
        others = [x for x in r["yaos"] if x is not y]
        print(f"  ✓ 取 {y.position}爻 {y.ganzhi()}{y.wuxing}（{y.state or '旺衰未知'}）"
              + (f"；另現於 {'、'.join(str(o.position) + '爻' for o in others)}（兩現取動、旺、不空不破者）" if others else ""))
    else:
        fs = r.get("fushen")
        print("  ✗ 用神不上卦。")
        if fs:
            print(f"    伏神：本宮首卦第{fs['position']}爻 {fs['ganzhi']}{fs['wuxing']}（{fs['state'] or '旺衰未知'}），"
                  f"伏於 {fs['fei_yao']} 之下——{fs['fei_rel']}")
            print(f"    {fs['note']}")
        if r.get("bian_yongshen"):
            b = r["bian_yongshen"]
            print(f"    變爻化出用神：{'、'.join(f'{x.position}爻→{x.bian_zhi}' for x in b)}（事後才出現）")
    for key, label in (("yuanshen", "原神（生用神）"), ("jishen", "忌神（克用神）"), ("choushen", "仇神（克原神）")):
        lq, ys = r[key]
        if ys:
            desc = "、".join(f"{x.position}爻{x.zhi}{'動' if x.is_changing else ('暗動' if x.is_an_dong else '靜')}（{x.state or '—'}）" for x in ys)
        else:
            desc = "不上卦"
        print(f"  {label}：{lq}　{desc}")
    if r.get("verdict"):
        v = r["verdict"]
        print("\n【用神綜合】（方向性整理，解讀時以此為起點並結合問事情理）")
        for reason in v["reasons"]:
            print(f"  · {reason}")
        print(f"  ⇒ {v['label']}（方向分 {v['score']:+}）")
    print("\n【應期候選】")
    for tip in suggest_yingqi(h, y):
        print(f"  • {tip}")


# ============================================================================
# CLI
# ============================================================================

HELP = """\
用法：
  python najia.py annotate <binary> [--changing 1,3,5] [--at "YYYY-MM-DD HH:MM"] [--tz 8] [--ask 問事]
  python najia.py annotate <binary> [--changing ...] [--day 甲子] [--month 寅] [--ask 問事]
  python najia.py list-questions

  binary     6 字元 0/1，最左為上爻、最右為初爻
  --at       起卦的當地鐘面時間 → 自動算月建（依節氣）與日干支（23 時起算次日）
  --day      手動指定日干支（覆蓋 --at）
  --month    手動指定月建地支（覆蓋 --at；須以節氣為界，不是農曆月）
  --ask      問事類型（見 list-questions）
"""


def _parse_args(argv: List[str]) -> Dict:
    args = {"binary": None, "changing": [], "day": None, "month": None, "ask": None,
            "at": None, "tz": cal.DEFAULT_TZ_HOURS}
    if len(argv) < 2:
        return args
    args["binary"] = argv[1]
    i = 2
    while i < len(argv):
        flag = argv[i]
        val = argv[i + 1] if i + 1 < len(argv) else None
        if flag == "--changing" and val is not None:
            args["changing"] = [int(x) for x in val.split(",") if x.strip()]
        elif flag in ("--day", "--month", "--ask", "--at") and val is not None:
            args[flag[2:]] = val
        elif flag == "--tz" and val is not None:
            args["tz"] = float(val)
        else:
            i += 1
            continue
        i += 2
    return args


def resolve_day_month(day: Optional[str], month: Optional[str], at: Optional[str],
                      tz: float = cal.DEFAULT_TZ_HOURS) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """--at 推算日干支與月建；手動 --day/--month 優先。回傳 (日, 月, 說明)。"""
    note = None
    if at:
        when = cal.parse_local(at)
        p = cal.pillars(when, tz)
        day = day or p["日"]
        month = month or p["月建"]
        note = (f"{when:%Y-%m-%d %H:%M}（UTC{tz:+g}）：{p['年']}年 {p['月']}月 {p['日']}日 {p['時支']}時"
                + ("　⚠距交節不足約30分鐘，月建或差一月" if p["近交節"] else "")
                + ("　（23時起算次日）" if p["子時推日"] else ""))
    return day, month, note


def main(argv: List[str]) -> None:
    if len(argv) < 2 or argv[1] in ("help", "-h", "--help"):
        print(HELP)
        return
    if argv[1] == "list-questions":
        print("可用問事類型（→ 用神）：")
        for k, v in YONGSHEN_MAP.items():
            print(f"  {k:<8} → {v}")
        return
    if argv[1] != "annotate" or len(argv) < 3:
        print(HELP)
        sys.exit(1)
    args = _parse_args(["annotate", argv[2]] + argv[3:])
    b = args["binary"]
    if not b or len(b) != 6 or any(c not in "01" for c in b):
        print("錯誤：binary 必須是 6 字元 0/1")
        sys.exit(1)
    day, month, note = resolve_day_month(args["day"], args["month"], args["at"], args["tz"])
    if note:
        print(f"占時：{note}")
    h = annotate(b, args["changing"], day, month)
    print_hexagram(h)
    if args["ask"]:
        print_yongshen(h, find_yongshen(h, args["ask"]))


if __name__ == "__main__":
    configure_stdout()
    main(sys.argv)
