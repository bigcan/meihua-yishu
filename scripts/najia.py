#!/usr/bin/env python3
"""
納甲（六爻）標註工具
Najia (Liu Yao) Annotation Engine

對任一六十四卦進行傳統「裝卦」：
- 每爻納甲（天干、地支、五行）
- 八宮歸屬、世爻、應爻
- 六親（父母、兄弟、子孫、妻財、官鬼）
- 六獸（青龍、朱雀、勾陳、螣蛇、白虎、玄武）→ 需日干
- 旬空 → 需日干支
- 月破、日破、六沖、六合、三合
- 動爻變化後的爻與六親
- 伏神（用神不上卦時從本宮首卦取）
- 反吟、伏吟
- 進神、退神
- 用神判定（依問事類型）
- 應期建議

可獨立使用，亦可被 jinqian_gua.py 呼叫。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from meihua_calc import BAGUA, HEXAGRAMS, BINARY_TO_GUA, apply_change, binary_to_gua_pair

# ============================================================================
# 核心對照表
# ============================================================================

# 天干
TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
# 地支
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
# 地支五行
ZHI_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}
# 天干五行（用於六獸起例外，五行生克本身用地支五行）
GAN_WUXING = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火",
    "戊": "土", "己": "土", "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}
# 天干陰陽
GAN_YINYANG = {
    "甲": "陽", "乙": "陰", "丙": "陽", "丁": "陰", "戊": "陽",
    "己": "陰", "庚": "陽", "辛": "陰", "壬": "陽", "癸": "陰",
}

# 八純卦的六爻納甲表（自初爻到上爻，每元素為「干+支」字串）
# 規則：
#   乾納甲壬（內甲外壬）、坤納乙癸（內乙外癸）
#   震納庚（全）、巽納辛（全）
#   坎納戊（全）、離納己（全）
#   艮納丙（全）、兌納丁（全）
# 地支：
#   乾外：午申戌；乾內：子寅辰（隔位順行，陽支）
#   坤外：丑亥酉；坤內：未巳卯（隔位逆行，陰支）
#   震：庚子寅辰午申戌（陽支順行）
#   巽：辛丑亥酉未巳卯（陰支逆行）
#   坎：戊寅辰午申戌子（陽支順行，從寅起）
#   離：己卯丑亥酉未巳（陰支逆行，從卯起）
#   艮：丙辰午申戌子寅（陽支順行，從辰起）
#   兌：丁巳卯丑亥酉未（陰支逆行，從巳起）
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

# 八宮五行（決定六親的「我」）
PALACE_WUXING = {
    1: "金", 2: "金",            # 乾、兌
    3: "火",                     # 離
    4: "木", 5: "木",            # 震、巽
    6: "水",                     # 坎
    7: "土", 8: "土",            # 艮、坤
}

PALACE_NAME = {1: "乾", 2: "兌", 3: "離", 4: "震", 5: "巽", 6: "坎", 7: "艮", 8: "坤"}

# 八宮卦序（從本宮卦到歸魂卦的 8 卦序號）
# 順序：本宮、一世、二世、三世、四世、五世、游魂、歸魂
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

# 反查：卦號 → (宮, 世代序 0..7)
HEX_TO_PALACE: Dict[int, Tuple[int, int]] = {}
for _palace, _seq in PALACE_ORDER.items():
    for _gen, _hex in enumerate(_seq):
        HEX_TO_PALACE[_hex] = (_palace, _gen)

# 世位/應位（依世代序 0..7）
# 0=本宮(世上應三)、1..5=一至五世、6=游魂(世四應初)、7=歸魂(世三應上)
SHI_POS = [6, 1, 2, 3, 4, 5, 4, 3]
YING_POS = [3, 4, 5, 6, 1, 2, 1, 6]
GENERATION_NAME = ["本宮", "一世", "二世", "三世", "四世", "五世", "游魂", "歸魂"]

# 五行生克
WUXING_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WUXING_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 六獸：依日干決定初爻起獸（自下而上順序固定為 青朱勾螣白玄）
LIUSHOU_ORDER = ["青龍", "朱雀", "勾陳", "螣蛇", "白虎", "玄武"]
LIUSHOU_START = {
    "甲": 0, "乙": 0,  # 青龍
    "丙": 1, "丁": 1,  # 朱雀
    "戊": 2,          # 勾陳
    "己": 3,          # 螣蛇
    "庚": 4, "辛": 4,  # 白虎
    "壬": 5, "癸": 5,  # 玄武
}

# 旬空：六十甲子分六旬，各旬空兩支
# 旬首 → (旬內 10 個干支, 空 2 支)
XUN_KONG = {
    "甲子": (["甲子", "乙丑", "丙寅", "丁卯", "戊辰", "己巳", "庚午", "辛未", "壬申", "癸酉"], ["戌", "亥"]),
    "甲戌": (["甲戌", "乙亥", "丙子", "丁丑", "戊寅", "己卯", "庚辰", "辛巳", "壬午", "癸未"], ["申", "酉"]),
    "甲申": (["甲申", "乙酉", "丙戌", "丁亥", "戊子", "己丑", "庚寅", "辛卯", "壬辰", "癸巳"], ["午", "未"]),
    "甲午": (["甲午", "乙未", "丙申", "丁酉", "戊戌", "己亥", "庚子", "辛丑", "壬寅", "癸卯"], ["辰", "巳"]),
    "甲辰": (["甲辰", "乙巳", "丙午", "丁未", "戊申", "己酉", "庚戌", "辛亥", "壬子", "癸丑"], ["寅", "卯"]),
    "甲寅": (["甲寅", "乙卯", "丙辰", "丁巳", "戊午", "己未", "庚申", "辛酉", "壬戌", "癸亥"], ["子", "丑"]),
}
GANZHI_TO_XUNKONG: Dict[str, List[str]] = {}
for _xun_head, (_gz_list, _kong) in XUN_KONG.items():
    for _gz in _gz_list:
        GANZHI_TO_XUNKONG[_gz] = _kong

# 六沖、六合、三合
LIU_CHONG = {
    "子": "午", "午": "子", "丑": "未", "未": "丑",
    "寅": "申", "申": "寅", "卯": "酉", "酉": "卯",
    "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳",
}
LIU_HE = {
    "子": "丑", "丑": "子", "寅": "亥", "亥": "寅",
    "卯": "戌", "戌": "卯", "辰": "酉", "酉": "辰",
    "巳": "申", "申": "巳", "午": "未", "未": "午",
}
SAN_HE = {
    frozenset(["申", "子", "辰"]): "水局",
    frozenset(["亥", "卯", "未"]): "木局",
    frozenset(["寅", "午", "戌"]): "火局",
    frozenset(["巳", "酉", "丑"]): "金局",
}

# 進神、退神：陽支順行為進神，逆行為退神
# 進神序列：寅→卯（木）、巳→午（火）、申→酉（金）、亥→子（水）、丑→辰→未→戌（土，旺）
# 退神：與進神相反
PROGRESS_PAIRS = {"寅": "卯", "巳": "午", "申": "酉", "亥": "子",
                  "丑": "辰", "辰": "未", "未": "戌"}
# 反向則為退神（值→鍵）
REGRESS_PAIRS = {v: k for k, v in PROGRESS_PAIRS.items() if k not in ("辰", "未", "戌")}
# 土的退神比較複雜（戌→未→辰→丑），加上
REGRESS_PAIRS.update({"戌": "未", "未": "辰", "辰": "丑"})

# 用神對照（問事 → 六親）
YONGSHEN_MAP = {
    "自身": "兄弟", "兄弟": "兄弟", "姐妹": "兄弟", "朋友": "兄弟",
    "同事": "兄弟", "夥伴": "兄弟", "競爭對手": "兄弟",
    "父母": "父母", "長輩": "父母", "師長": "父母", "上司（敬重者）": "父母",
    "房屋": "父母", "車輛": "父母", "船車": "父母", "文書": "父母",
    "契約": "父母", "學業": "父母", "證件": "父母", "信件": "父母",
    "子女": "子孫", "晚輩": "子孫", "下屬": "子孫", "學生": "子孫",
    "寵物": "子孫", "六畜": "子孫", "藥物": "子孫", "醫生": "子孫",
    "出行": "子孫", "僧道": "子孫", "解神": "子孫",
    "妻子": "妻財", "妾": "妻財", "情人（女）": "妻財",
    "財物": "妻財", "錢財": "妻財", "薪資": "妻財", "買賣": "妻財",
    "求財": "妻財", "貨物": "妻財", "物品": "妻財",
    "丈夫": "官鬼", "情人（男）": "官鬼", "工作": "官鬼", "事業": "官鬼",
    "官位": "官鬼", "功名": "官鬼", "考試": "官鬼", "升遷": "官鬼",
    "疾病": "官鬼", "災禍": "官鬼", "鬼神": "官鬼", "盜賊": "官鬼",
    "訴訟": "官鬼", "對手（強）": "官鬼",
}

# 六親五行對應關係（以宮卦五行為「我」）
# 同我=兄弟、生我=父母、我生=子孫、克我=官鬼、我克=妻財
def liuqin_from(palace_wuxing: str, yao_wuxing: str) -> str:
    if yao_wuxing == palace_wuxing:
        return "兄弟"
    if WUXING_SHENG[yao_wuxing] == palace_wuxing:
        return "父母"
    if WUXING_SHENG[palace_wuxing] == yao_wuxing:
        return "子孫"
    if WUXING_KE[yao_wuxing] == palace_wuxing:
        return "官鬼"
    if WUXING_KE[palace_wuxing] == yao_wuxing:
        return "妻財"
    return "?"


# ============================================================================
# 卦結構推導
# ============================================================================

def hex_najia(upper: int, lower: int) -> List[str]:
    """
    某六十四卦的六爻納甲（自下而上 6 條干支字串）
    規則：下三爻取下卦純卦的下三爻，上三爻取上卦純卦的上三爻
    """
    lower_nj = PURE_GUA_NAJIA[lower][:3]
    upper_nj = PURE_GUA_NAJIA[upper][3:]
    return lower_nj + upper_nj


@dataclass
class YaoNajia:
    position: int          # 1..6
    is_yang: bool          # 本爻陰陽
    gan: str               # 天干
    zhi: str               # 地支
    wuxing: str            # 地支五行
    liuqin: str            # 六親
    liushou: Optional[str] = None
    is_shi: bool = False
    is_ying: bool = False
    is_changing: bool = False
    bian_zhi: Optional[str] = None
    bian_wuxing: Optional[str] = None
    bian_liuqin: Optional[str] = None
    is_void: bool = False     # 旬空
    is_ri_chong: bool = False # 被日沖
    is_yue_chong: bool = False # 被月沖
    is_ri_he: bool = False    # 與日合
    note: List[str] = field(default_factory=list)

    def ganzhi(self) -> str:
        return self.gan + self.zhi


@dataclass
class AnnotatedHexagram:
    upper: int
    lower: int
    hex_num: int
    hex_name: str
    palace: int            # 1..8
    palace_name: str       # 乾/兌/...
    generation: int        # 0..7
    generation_name: str   # 本宮/一世/.../歸魂
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
    notes: List[str] = field(default_factory=list)


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
    對一個 6 位二進位本卦做完整納甲標註

    Args:
        binary: 6 字元 0/1，最左為上爻、最右為初爻（與 meihua_calc 一致）
        changing: 動爻位置列表（1..6，由下往上）；None 視為無動爻
        day_ganzhi: 日干支（例 "甲子"）；用於六獸、旬空、日破/日合
        month_zhi: 月支（例 "寅"）；用於月破/月合

    Returns:
        AnnotatedHexagram 完整裝卦結果
    """
    changing = changing or []
    upper, lower = binary_to_gua_pair(binary)
    hex_num, hex_name = HEXAGRAMS[(upper, lower)]
    palace, generation = HEX_TO_PALACE[hex_num]
    palace_wuxing = PALACE_WUXING[palace]
    shi = SHI_POS[generation]
    ying = YING_POS[generation]

    nj = hex_najia(upper, lower)
    yaos: List[YaoNajia] = []
    for i in range(6):
        position = i + 1
        is_yang = binary[6 - position] == "1"
        gz = nj[i]
        gan, zhi = gz[0], gz[1]
        wuxing = ZHI_WUXING[zhi]
        liuqin = liuqin_from(palace_wuxing, wuxing)
        yao = YaoNajia(
            position=position,
            is_yang=is_yang,
            gan=gan,
            zhi=zhi,
            wuxing=wuxing,
            liuqin=liuqin,
            is_shi=(position == shi),
            is_ying=(position == ying),
            is_changing=(position in changing),
        )
        yaos.append(yao)

    # 動爻變化後的爻
    bian_upper = bian_lower = bian_hex_num = bian_hex_name = None
    bian_palace = bian_palace_name = None
    if changing:
        bian_bin = binary
        for p in changing:
            bian_bin = apply_change(bian_bin, p)
        bian_upper, bian_lower = binary_to_gua_pair(bian_bin)
        bian_hex_num, bian_hex_name = HEXAGRAMS[(bian_upper, bian_lower)]
        b_palace, _ = HEX_TO_PALACE[bian_hex_num]
        bian_palace = b_palace
        bian_palace_name = PALACE_NAME[b_palace]
        bian_nj = hex_najia(bian_upper, bian_lower)
        for y in yaos:
            if y.is_changing:
                bgz = bian_nj[y.position - 1]
                y.bian_zhi = bgz[1]
                y.bian_wuxing = ZHI_WUXING[y.bian_zhi]
                # 注意：變爻六親仍以「本卦的宮」為我來判定
                y.bian_liuqin = liuqin_from(palace_wuxing, y.bian_wuxing)

    # 六獸（依日干）
    if day_ganzhi:
        day_gan = day_ganzhi[0]
        if day_gan in LIUSHOU_START:
            start = LIUSHOU_START[day_gan]
            for i in range(6):
                yaos[i].liushou = LIUSHOU_ORDER[(start + i) % 6]

    # 旬空
    void_zhis: List[str] = []
    if day_ganzhi and day_ganzhi in GANZHI_TO_XUNKONG:
        void_zhis = GANZHI_TO_XUNKONG[day_ganzhi]
        for y in yaos:
            if y.zhi in void_zhis:
                y.is_void = True

    # 日沖、日合
    if day_ganzhi:
        day_zhi = day_ganzhi[1]
        for y in yaos:
            if LIU_CHONG.get(y.zhi) == day_zhi:
                y.is_ri_chong = True
            if LIU_HE.get(y.zhi) == day_zhi:
                y.is_ri_he = True

    # 月沖
    if month_zhi:
        for y in yaos:
            if LIU_CHONG.get(y.zhi) == month_zhi:
                y.is_yue_chong = True

    annotated = AnnotatedHexagram(
        upper=upper, lower=lower,
        hex_num=hex_num, hex_name=hex_name,
        palace=palace, palace_name=PALACE_NAME[palace],
        generation=generation, generation_name=GENERATION_NAME[generation],
        palace_wuxing=palace_wuxing,
        shi_pos=shi, ying_pos=ying,
        yaos=yaos,
        bian_upper=bian_upper, bian_lower=bian_lower,
        bian_hex_num=bian_hex_num, bian_hex_name=bian_hex_name,
        bian_palace=bian_palace, bian_palace_name=bian_palace_name,
        day_ganzhi=day_ganzhi, month_zhi=month_zhi,
    )

    # 進階分析
    _detect_fanyin_fuyin(annotated)
    _detect_jin_tui(annotated)
    _detect_sanhe_liuhe(annotated)

    return annotated


# ============================================================================
# 進階分析（Phase 3）
# ============================================================================

def _detect_fanyin_fuyin(h: AnnotatedHexagram) -> None:
    """檢測反吟、伏吟"""
    if not h.bian_hex_num:
        return
    # 反吟：本卦變卦六爻地支兩兩相沖
    # 伏吟：本卦變卦六爻地支兩兩相同
    bian_nj = hex_najia(h.bian_upper, h.bian_lower)  # type: ignore[arg-type]
    chong_count = he_count = same_count = 0
    for i, y in enumerate(h.yaos):
        b_zhi = bian_nj[i][1]
        if b_zhi == y.zhi:
            same_count += 1
        if LIU_CHONG.get(y.zhi) == b_zhi:
            chong_count += 1
    if chong_count >= 3:
        h.notes.append(f"反吟（{chong_count} 爻本變相沖）：事情反覆、傷悲")
    if same_count >= 3:
        h.notes.append(f"伏吟（{same_count} 爻本變相同）：呻吟憂愁、停滯不前")

    # 卦反吟：上下卦地支天干完全相沖（八純卦變八純卦的特例）
    if h.upper == h.bian_lower and h.lower == h.bian_upper:
        h.notes.append("卦反吟：上下卦相易，動盪不安")


def _detect_jin_tui(h: AnnotatedHexagram) -> None:
    """檢測進神、退神（針對動爻）"""
    for y in h.yaos:
        if not y.is_changing or not y.bian_zhi:
            continue
        if PROGRESS_PAIRS.get(y.zhi) == y.bian_zhi:
            y.note.append("進神（吉象：順勢前進）")
        elif REGRESS_PAIRS.get(y.zhi) == y.bian_zhi:
            y.note.append("退神（事情後退、力量減弱）")


def _detect_sanhe_liuhe(h: AnnotatedHexagram) -> None:
    """檢測卦中三合局、六合"""
    zhis = [y.zhi for y in h.yaos]
    zhi_set = set(zhis)
    for combo, name in SAN_HE.items():
        if combo.issubset(zhi_set):
            positions = [str(y.position) for y in h.yaos if y.zhi in combo]
            h.notes.append(f"卦中三合{name}（爻位 {'、'.join(positions)}）：聚合有力")
    # 卦逢六合：六爻中存在六合對
    for i in range(6):
        for j in range(i + 1, 6):
            if LIU_HE.get(zhis[i]) == zhis[j]:
                pass  # 太多了，不每對都報；只報關鍵
    # 簡化：上下卦六合（傳統六合卦）— 留給 SKILL.md 判斷


# ============================================================================
# 用神 / 伏神
# ============================================================================

def find_yongshen(h: AnnotatedHexagram, question_type: str) -> Dict:
    """
    依問事類型找用神
    Returns:
        {
          'liuqin': '...',          # 用神六親
          'yaos': [YaoNajia, ...],  # 卦中該六親的爻（可能 0 或多個）
          'fushen': Optional[Dict], # 若不上卦，從本宮首卦取伏神
        }
    """
    if question_type not in YONGSHEN_MAP:
        return {"error": f"未知問事類型：{question_type}，可用類型見 YONGSHEN_MAP"}
    target = YONGSHEN_MAP[question_type]
    matches = [y for y in h.yaos if y.liuqin == target]
    result = {"question_type": question_type, "liuqin": target, "yaos": matches, "fushen": None}
    if not matches:
        # 用神不上卦 → 從本宮首卦（八純卦）取伏神
        result["fushen"] = _find_fushen(h, target)
    return result


def _find_fushen(h: AnnotatedHexagram, target_liuqin: str) -> Optional[Dict]:
    """從本宮首卦（八純卦）找對應六親作為伏神"""
    pure_nj = PURE_GUA_NAJIA[h.palace]
    for i, gz in enumerate(pure_nj):
        zhi = gz[1]
        wuxing = ZHI_WUXING[zhi]
        liuqin = liuqin_from(h.palace_wuxing, wuxing)
        if liuqin == target_liuqin:
            return {
                "position": i + 1,
                "ganzhi": gz,
                "wuxing": wuxing,
                "liuqin": liuqin,
                "fei_yao": h.yaos[i].ganzhi() + f"（{h.yaos[i].liuqin}）",
                "note": "伏神藏於本宮首卦，需飛神生扶或日月引出才能起作用",
            }
    return None


# ============================================================================
# 應期建議
# ============================================================================

def suggest_yingqi(h: AnnotatedHexagram, yongshen_yao: Optional[YaoNajia]) -> List[str]:
    """
    應期推算建議（傳統六爻法綜合）
    """
    if not yongshen_yao:
        return ["用神不上卦或未指定，應期難定；建議以伏神出現之日/月為期。"]
    tips = []
    zhi = yongshen_yao.zhi
    # 沖實之日
    chong = LIU_CHONG.get(zhi)
    if chong:
        tips.append(f"逢沖實之日：{chong} 日／月")
    he = LIU_HE.get(zhi)
    if he:
        tips.append(f"逢合之日：{he} 日／月")
    if yongshen_yao.is_void:
        tips.append("用神旬空：出旬之日、或值日、或沖空之日應期")
    if yongshen_yao.is_changing:
        tips.append("用神動：值日或變爻地支之日應期")
    if not tips:
        tips.append("一般：值用神地支之日／月應期")
    return tips


# ============================================================================
# 輸出
# ============================================================================

def print_hexagram(h: AnnotatedHexagram) -> None:
    print("\n" + "=" * 64)
    print(f"📜 納甲裝卦：第{h.hex_num}卦 {h.hex_name}")
    print(f"   歸宮：{h.palace_name}宮 {h.generation_name}卦  宮五行：{h.palace_wuxing}")
    print(f"   世爻：第{h.shi_pos}爻   應爻：第{h.ying_pos}爻")
    if h.day_ganzhi:
        kong = "、".join(GANZHI_TO_XUNKONG.get(h.day_ganzhi, []))
        print(f"   日干支：{h.day_ganzhi}  旬空：{kong}")
    if h.month_zhi:
        print(f"   月支：{h.month_zhi}")
    print("=" * 64)

    # 自上而下印爻
    print(f"\n{'六獸':<4} {'六親':<4} {'干支':<5} {'五行':<3} {'爻':<8} {'位':<5} {'動變':<10} 備註")
    print("-" * 80)
    for y in reversed(h.yaos):
        liushou = (y.liushou or "  ").ljust(4)
        liuqin = y.liuqin.ljust(4)
        gz = y.ganzhi().ljust(5)
        wx = y.wuxing.ljust(3)
        line = _yao_line(y).ljust(8)
        pos_marks = []
        if y.is_shi: pos_marks.append("世")
        if y.is_ying: pos_marks.append("應")
        pos = ("第" + str(y.position) + "爻 " + "".join(pos_marks)).ljust(5)
        bian = ""
        if y.is_changing:
            bian = f"→{y.bian_zhi}{y.bian_wuxing}({y.bian_liuqin})"
        bian = bian.ljust(10)
        notes = []
        if y.is_void: notes.append("旬空")
        if y.is_ri_chong: notes.append("日破")
        if y.is_yue_chong: notes.append("月破")
        if y.is_ri_he: notes.append("日合")
        notes.extend(y.note)
        note_str = "、".join(notes)
        print(f"{liushou} {liuqin} {gz} {wx} {line} {pos} {bian} {note_str}")

    if h.bian_hex_num:
        print(f"\n變卦：第{h.bian_hex_num}卦 {h.bian_hex_name}  歸宮：{h.bian_palace_name}宮")

    if h.notes:
        print("\n【整體判斷】")
        for n in h.notes:
            print(f"  • {n}")


def _yao_line(y: YaoNajia) -> str:
    if y.is_yang and y.is_changing:
        return "▅▅O▅▅"
    if y.is_yang:
        return "▅▅▅▅▅"
    if y.is_changing:
        return "▅▅X▅▅"
    return "▅▅ ▅▅"


def print_yongshen(h: AnnotatedHexagram, ys_result: Dict) -> None:
    print("\n【用神判定】")
    if "error" in ys_result:
        print(f"  {ys_result['error']}")
        return
    qt = ys_result["question_type"]
    lq = ys_result["liuqin"]
    matches = ys_result["yaos"]
    print(f"  問事類型：{qt} → 用神取「{lq}」")
    if matches:
        for y in matches:
            tags = []
            if y.is_shi: tags.append("世")
            if y.is_ying: tags.append("應")
            if y.is_void: tags.append("旬空")
            if y.is_changing: tags.append("動")
            tag_str = f"［{'、'.join(tags)}］" if tags else ""
            print(f"  ✓ 第{y.position}爻 {y.ganzhi()}({y.wuxing}) {tag_str}")
        # 應期
        primary = matches[0]
        for y in matches:  # 優先取動爻
            if y.is_changing:
                primary = y
                break
        print(f"\n【應期建議】（基於第{primary.position}爻 用神）")
        for tip in suggest_yingqi(h, primary):
            print(f"  • {tip}")
    else:
        fs = ys_result["fushen"]
        if fs:
            print(f"  ✗ 用神不上卦，伏神在本宮首卦：")
            print(f"    第{fs['position']}爻 {fs['ganzhi']}（{fs['liuqin']}）")
            print(f"    飛神：{fs['fei_yao']}")
            print(f"    {fs['note']}")
        else:
            print("  ✗ 用神不上卦，且本宮首卦無此六親")


# ============================================================================
# CLI
# ============================================================================

HELP = """\
用法：
  python najia.py annotate <binary> [--changing 1,3,5] [--day 甲子] [--month 寅] [--ask 問事類型]

參數：
  binary       6 字元 0/1，最左為上爻、最右為初爻（與 jinqian_gua 一致）
  --changing   動爻位置（逗號分隔，自下往上 1..6）
  --day        日干支（兩字，如 甲子、丙午）
  --month      月支（一字，如 寅、卯）
  --ask        問事類型（自身/兄弟/父母/子女/妻財/丈夫/工作/疾病/求財/...）

範例：
  python najia.py annotate 011010 --changing 5 --day 甲子 --month 寅 --ask 求財
  python najia.py annotate 111000                            # 純裝卦
  python najia.py list-questions                             # 列出所有問事類型
"""


def _parse_args(argv: List[str]) -> Dict:
    args = {"binary": None, "changing": [], "day": None, "month": None, "ask": None}
    if len(argv) < 2:
        return args
    args["binary"] = argv[1]
    i = 2
    while i < len(argv):
        flag = argv[i]
        if flag == "--changing" and i + 1 < len(argv):
            args["changing"] = [int(x) for x in argv[i + 1].split(",") if x.strip()]
            i += 2
        elif flag == "--day" and i + 1 < len(argv):
            args["day"] = argv[i + 1]
            i += 2
        elif flag == "--month" and i + 1 < len(argv):
            args["month"] = argv[i + 1]
            i += 2
        elif flag == "--ask" and i + 1 < len(argv):
            args["ask"] = argv[i + 1]
            i += 2
        else:
            i += 1
    return args


def main(argv: List[str]) -> None:
    if len(argv) < 2 or argv[1] in ("help", "-h", "--help"):
        print(HELP)
        return
    if argv[1] == "list-questions":
        print("可用問事類型（→ 用神）：")
        for k, v in YONGSHEN_MAP.items():
            print(f"  {k:<14} → {v}")
        return
    if argv[1] != "annotate":
        print(f"未知指令：{argv[1]}\n")
        print(HELP)
        sys.exit(1)
    args = _parse_args(argv[1:])  # 把 annotate 視為占位，binary 從 argv[2] 取
    args["binary"] = argv[2] if len(argv) > 2 else None
    # 重新解析後續 flag
    rest_args = _parse_args(["annotate", argv[2]] + argv[3:])
    args = rest_args

    if not args["binary"] or len(args["binary"]) != 6 or any(c not in "01" for c in args["binary"]):
        print("錯誤：binary 必須是 6 字元 0/1")
        sys.exit(1)

    h = annotate(args["binary"], args["changing"], args["day"], args["month"])
    print_hexagram(h)
    if args["ask"]:
        ys = find_yongshen(h, args["ask"])
        print_yongshen(h, ys)


if __name__ == "__main__":
    main(sys.argv)
