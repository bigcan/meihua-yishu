#!/usr/bin/env python3
"""
金錢卦（六爻）起卦工具
Coin Divination (Liu Yao) Calculator

3 枚銅錢擲 6 次成卦，自下而上記爻。
支援：隨機模擬、手動輸入、朱熹《易學啟蒙》多動爻解卦法。

與梅花易數的差異：
- 梅花易數：起卦只有 1 個動爻
- 金錢卦：起卦可有 0~6 個動爻，需依朱熹法判斷主爻

可進一步透過 najia.py 加上納甲（六親、六獸、世應、旬空）做完整六爻斷卦。
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# 與 meihua_calc.py 共用的 BAGUA / HEXAGRAMS / stdout 編碼處理
from meihua_calc import (
    BAGUA,
    HEXAGRAMS,
    binary_to_gua_pair,
    configure_stdout,
    get_hu_gua,
)

# 銅錢約定：背為陽(3)、字為陰(2)
# 用戶輸入符號對照
COIN_SYMBOLS = {
    "背": 3, "陽": 3, "正": 3, "花": 3, "h": 3, "H": 3, "1": 3, "+": 3,
    "字": 2, "陰": 2, "反": 2, "t": 2, "T": 2, "0": 2, "-": 2,
}

# 4 種爻象
# (sum, 名稱, 符號, 是否陽爻, 是否動爻)
YAO_TYPES = {
    6: ("老陰", "X", False, True),   # 三字  → 陰變陽
    7: ("少陽", "—", True, False),   # 一背  → 陽不動
    8: ("少陰", "- -", False, False),# 二背  → 陰不動
    9: ("老陽", "O", True, True),    # 三背  → 陽變陰
}

# 朱熹《易學啟蒙》動爻解卦法
ZHUXI_RULES = {
    0: "看本卦卦辭（無動爻）",
    1: "看本卦該動爻爻辭",
    2: "看本卦兩動爻爻辭，以上爻為主",
    3: "看本卦卦辭 + 變卦卦辭，本卦為貞、變卦為悔",
    4: "看變卦兩不動爻爻辭，以下爻為主",
    5: "看變卦唯一不動爻爻辭",
    6: "看變卦卦辭（乾「用九」、坤「用六」例外）",
}


@dataclass
class Yao:
    """單一爻"""
    position: int          # 1=初爻（最下）, 6=上爻
    coins: List[int]       # 3 枚銅錢結果 [3,3,2] 等
    total: int = field(init=False)
    name: str = field(init=False)
    symbol: str = field(init=False)
    is_yang: bool = field(init=False)
    is_changing: bool = field(init=False)

    def __post_init__(self) -> None:
        if len(self.coins) != 3:
            raise ValueError(f"每次需擲 3 枚銅錢，收到 {len(self.coins)} 枚")
        for c in self.coins:
            if c not in (2, 3):
                raise ValueError(f"銅錢值只能為 2(字/陰) 或 3(背/陽)，收到 {c}")
        self.total = sum(self.coins)
        # symbol 為對外顯示用（保留向後相容欄位）
        self.name, self.symbol, self.is_yang, self.is_changing = YAO_TYPES[self.total]

    def coin_display(self) -> str:
        return "".join("背" if c == 3 else "字" for c in self.coins)


@dataclass
class CoinHexagram:
    """金錢卦的完整六爻結果"""
    yaos: List[Yao]   # 由下而上：[初爻, 二爻, 三爻, 四爻, 五爻, 上爻]

    def __post_init__(self) -> None:
        if len(self.yaos) != 6:
            raise ValueError(f"金錢卦需 6 爻，收到 {len(self.yaos)}")

    def ben_binary(self) -> str:
        """本卦二進位（上爻在前，下爻在後，與 meihua_calc 約定一致）"""
        # yaos[0]=初爻；二進位最右端為初爻
        return "".join("1" if y.is_yang else "0" for y in reversed(self.yaos))

    def bian_binary(self) -> str:
        """變卦二進位（所有動爻陰陽互換）"""
        bits = list(self.ben_binary())
        for y in self.yaos:
            if y.is_changing:
                idx = 6 - y.position  # 與 meihua_calc.apply_change 一致
                bits[idx] = "0" if bits[idx] == "1" else "1"
        return "".join(bits)

    def changing_positions(self) -> List[int]:
        return [y.position for y in self.yaos if y.is_changing]


# ----------------------------------------------------------------------------
# 擲卦來源
# ----------------------------------------------------------------------------

def throw_one_yao(rng: Optional[random.Random] = None) -> List[int]:
    """模擬擲 3 枚銅錢一次"""
    rng = rng or random
    return [rng.choice([2, 3]) for _ in range(3)]


def random_hexagram(seed: Optional[int] = None) -> CoinHexagram:
    """隨機擲 6 次成卦（自下而上）"""
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    yaos = [Yao(position=i + 1, coins=throw_one_yao(rng)) for i in range(6)]
    return CoinHexagram(yaos=yaos)


def parse_throw_string(text: str) -> List[int]:
    """
    解析一次擲卦的字串輸入。
    接受：
      - "背背字" / "背字字" / "字字字"
      - "陽陽陰"
      - "HHT" / "110"  (1=背=3, 0=字=2)
      - "+,+,-" 以逗號分隔亦可
    """
    cleaned = [ch for ch in text if not ch.isspace() and ch not in (",", "，", "/", "|")]
    if len(cleaned) != 3:
        raise ValueError(f"每次需 3 個銅錢符號，收到 {len(cleaned)} 個：{text!r}")
    coins = []
    for ch in cleaned:
        if ch not in COIN_SYMBOLS:
            raise ValueError(f"無法辨識符號 {ch!r}（用 背/字/陽/陰/H/T/1/0）")
        coins.append(COIN_SYMBOLS[ch])
    return coins


def manual_hexagram(throws: List[str]) -> CoinHexagram:
    """
    手動輸入 6 次擲卦結果。
    throws[0] = 第一次擲（初爻 / 最下爻）
    throws[5] = 第六次擲（上爻 / 最上爻）
    """
    if len(throws) != 6:
        raise ValueError(f"金錢卦需 6 次擲卦，收到 {len(throws)} 次")
    yaos = [Yao(position=i + 1, coins=parse_throw_string(t)) for i, t in enumerate(throws)]
    return CoinHexagram(yaos=yaos)


# ----------------------------------------------------------------------------
# 解卦
# ----------------------------------------------------------------------------

def analyze(hex_: CoinHexagram) -> dict:
    """完整分析金錢卦結果"""
    ben_bin = hex_.ben_binary()
    bian_bin = hex_.bian_binary()

    ben_upper, ben_lower = binary_to_gua_pair(ben_bin)
    bian_upper, bian_lower = binary_to_gua_pair(bian_bin)

    ben_num, ben_name = HEXAGRAMS[(ben_upper, ben_lower)]
    bian_num, bian_name = HEXAGRAMS[(bian_upper, bian_lower)]

    # 互卦（純陽純陰特殊處理 → 從變卦取互卦）
    if ben_bin in ("111111", "000000"):
        if any(y.is_changing for y in hex_.yaos):
            hu_upper, hu_lower = get_hu_gua(bian_bin)
            hu_note = "（本卦為純陽/純陰，互卦取自變卦）"
        else:
            hu_upper, hu_lower = ben_upper, ben_lower
            hu_note = "（本卦為純陽/純陰且無動爻，互卦同本卦）"
    else:
        hu_upper, hu_lower = get_hu_gua(ben_bin)
        hu_note = ""
    hu_num, hu_name = HEXAGRAMS[(hu_upper, hu_lower)]

    changing = hex_.changing_positions()
    n_changing = len(changing)
    zhuxi = ZHUXI_RULES[n_changing]
    main_yao = _zhuxi_main_yao(hex_, changing)

    return {
        "本卦": {
            "序號": ben_num,
            "名稱": ben_name,
            "上卦": BAGUA[ben_upper]["name"],
            "下卦": BAGUA[ben_lower]["name"],
            "二進位": ben_bin,
        },
        "變卦": {
            "序號": bian_num,
            "名稱": bian_name,
            "上卦": BAGUA[bian_upper]["name"],
            "下卦": BAGUA[bian_lower]["name"],
            "二進位": bian_bin,
        },
        "互卦": {
            "名稱": hu_name,
            "上互": BAGUA[hu_upper]["name"],
            "下互": BAGUA[hu_lower]["name"],
            "註": hu_note,
        },
        "動爻": {
            "位置": changing,
            "數量": n_changing,
            "解卦法": zhuxi,
            "主爻": main_yao,
        },
        "爻象": [_yao_detail(y) for y in hex_.yaos],
    }


def _yao_detail(y: Yao) -> dict:
    return {
        "位置": y.position,
        "銅錢": y.coin_display(),
        "總和": y.total,
        "爻象": y.name,
        "陰陽": "陽" if y.is_yang else "陰",
        "動否": "動" if y.is_changing else "靜",
    }


def _zhuxi_main_yao(hex_: CoinHexagram, changing: List[int]) -> Optional[str]:
    """依朱熹法判定主爻"""
    n = len(changing)
    if n == 0:
        return None
    if n == 1:
        return f"本卦第{changing[0]}爻"
    if n == 2:
        return f"本卦第{max(changing)}爻（兩動以上爻為主）"
    if n == 3:
        return "本卦卦辭 + 變卦卦辭（本貞變悔）"
    static = [y.position for y in hex_.yaos if not y.is_changing]
    if n == 4:
        return f"變卦第{min(static)}爻（兩不動以下爻為主）"
    if n == 5:
        return f"變卦第{static[0]}爻"
    if n == 6:
        # 乾坤特殊
        ben_bin = hex_.ben_binary()
        if ben_bin == "111111":
            return "乾「用九：見群龍無首，吉」"
        if ben_bin == "000000":
            return "坤「用六：利永貞」"
        return "變卦卦辭"
    return None


def zhuxi_texts(hex_: CoinHexagram, ben_num: int, bian_num: int) -> List[str]:
    """依朱熹法列出應讀的卦爻辭原文（主者在前）。"""
    try:
        import yaoci_lookup as yl
    except ImportError:
        return []
    ch = hex_.changing_positions()
    static = [y.position for y in hex_.yaos if not y.is_changing]
    n = len(ch)
    try:
        if n == 0:
            return [yl.format_guaci(ben_num)]
        if n == 1:
            return [yl.format_line(ben_num, ch[0])]
        if n == 2:
            return ["（主）" + yl.format_line(ben_num, max(ch)), "（次）" + yl.format_line(ben_num, min(ch))]
        if n == 3:
            return ["（貞・本卦）" + yl.format_guaci(ben_num), "（悔・變卦）" + yl.format_guaci(bian_num)]
        if n == 4:
            return ["（主）" + yl.format_line(bian_num, min(static)), "（次）" + yl.format_line(bian_num, max(static))]
        if n == 5:
            return [yl.format_line(bian_num, static[0])]
        if ben_num in (1, 2):
            return [yl.format_line(ben_num, 7)]
        return [yl.format_guaci(bian_num)]
    except OSError:
        return []


# ----------------------------------------------------------------------------
# 輸出
# ----------------------------------------------------------------------------

def print_yao_diagram(hex_: CoinHexagram) -> None:
    """由上而下印出 6 爻（傳統裝卦方向）"""
    print("\n【爻象（自上而下）】")
    for y in reversed(hex_.yaos):
        # 動爻標記
        mark = "  ←動" if y.is_changing else ""
        # 爻畫
        if y.is_yang and y.is_changing:
            line = "▅▅O▅▅"
        elif y.is_yang:
            line = "▅▅▅▅▅"
        elif y.is_changing:  # 老陰
            line = "▅▅X▅▅"
        else:
            line = "▅▅ ▅▅"
        print(f"  第{y.position}爻 [{y.coin_display()}={y.total} {y.name}] {line}{mark}")


def print_result(
    hex_: CoinHexagram,
    result: Optional[dict] = None,
    najia_day: Optional[str] = None,
    najia_month: Optional[str] = None,
    najia_ask: Optional[str] = None,
    najia_at: Optional[str] = None,
    najia_tz: float = 8.0,
) -> None:
    result = result or analyze(hex_)
    print("\n" + "=" * 56)
    print("🪙 金錢卦（六爻）起卦結果")
    print("=" * 56)

    print_yao_diagram(hex_)

    ben = result["本卦"]
    print(f"\n【本卦】第{ben['序號']}卦 {ben['名稱']}（上{ben['上卦']} 下{ben['下卦']}） bin={ben['二進位']}")

    hu = result["互卦"]
    print(f"【互卦】{hu['名稱']}（上互{hu['上互']} 下互{hu['下互']}）{hu['註']}")

    bian = result["變卦"]
    print(f"【變卦】第{bian['序號']}卦 {bian['名稱']}（上{bian['上卦']} 下{bian['下卦']}） bin={bian['二進位']}")

    dong = result["動爻"]
    pos_str = "、".join(f"第{p}爻" for p in dong["位置"]) or "無"
    print(f"\n【動爻】共 {dong['數量']} 個：{pos_str}")
    print(f"【解卦法】{dong['解卦法']}")
    if dong["主爻"]:
        print(f"【主爻】{dong['主爻']}")
    for line in zhuxi_texts(hex_, ben["序號"], bian["序號"]):
        print(f"  ▶ {line}")

    # 納甲標註：有占時（--at）或手動日月時自動裝卦
    if najia_day or najia_month or najia_ask or najia_at:
        from najia import annotate as najia_annotate
        from najia import find_yongshen, print_hexagram, print_yongshen, resolve_day_month
        day, month, note = resolve_day_month(najia_day, najia_month, najia_at, najia_tz)
        if note:
            print(f"\n【占時】{note}")
        h = najia_annotate(ben["二進位"], changing=dong["位置"], day_ganzhi=day, month_zhi=month)
        print_hexagram(h)
        if najia_ask:
            print_yongshen(h, find_yongshen(h, najia_ask))
        else:
            print("\n提示：加 --ask <問事> 可定用神、原忌神與應期（python najia.py list-questions）")
    else:
        print("\n" + "=" * 56)
        print("提示：六爻斷卦必須有月建與日辰。加 --at \"YYYY-MM-DD HH:MM\"（起卦當地時間）")
        print("      與 --ask <問事>，即自動裝卦、判旺衰、定用神與應期。")
        print("=" * 56)


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def _split_najia_flags(args: List[str]) -> Tuple[List[str], dict]:
    """從 CLI args 中分離出 --day/--month/--ask 等納甲旗標，回傳 (剩餘 args, najia_kwargs)"""
    nj = {"najia_day": None, "najia_month": None, "najia_ask": None,
          "najia_at": None, "najia_tz": 8.0}
    out: List[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--day" and i + 1 < len(args):
            nj["najia_day"] = args[i + 1]
            i += 2
        elif a == "--month" and i + 1 < len(args):
            nj["najia_month"] = args[i + 1]
            i += 2
        elif a == "--ask" and i + 1 < len(args):
            nj["najia_ask"] = args[i + 1]
            i += 2
        elif a == "--at" and i + 1 < len(args):
            nj["najia_at"] = args[i + 1]
            i += 2
        elif a == "--tz" and i + 1 < len(args):
            nj["najia_tz"] = float(args[i + 1])
            i += 2
        else:
            out.append(a)
            i += 1
    return out, nj


def _cli_random(args: List[str]) -> None:
    args, nj = _split_najia_flags(args)
    if args and args[0] in ("-h", "--help", "help"):
        print(HELP)
        return
    seed = int(args[0]) if args and args[0].lstrip("-").isdigit() else None
    hex_ = random_hexagram(seed=seed)
    print_result(hex_, **nj)


def _cli_manual(args: List[str]) -> None:
    args, nj = _split_najia_flags(args)
    if len(args) != 6:
        print("錯誤：手動輸入需提供 6 次擲卦結果（自下而上）")
        print('範例：python jinqian_gua.py manual 背背字 字背字 背背背 字字字 背字背 字背背')
        sys.exit(1)
    hex_ = manual_hexagram(args)
    print_result(hex_, **nj)


def _cli_interactive(args: List[str]) -> None:
    _, nj = _split_najia_flags(args)
    print("=" * 56)
    print("🪙 金錢卦手動輸入（共 6 次，自下而上）")
    print("=" * 56)
    print("輸入符號：背/陽/1/H 表陽，字/陰/0/T 表陰；每次 3 個。")
    print("例：背背字 或 110 或 H,H,T 都可。")
    print()
    throws = []
    for i in range(1, 7):
        ordinal = {1: "初", 2: "二", 3: "三", 4: "四", 5: "五", 6: "上"}[i]
        while True:
            try:
                raw = input(f"第 {i} 次擲（第{ordinal}爻）: ").strip()
                if not raw:
                    continue
                parse_throw_string(raw)  # 驗證
                throws.append(raw)
                break
            except ValueError as e:
                print(f"  ✗ {e}，請重新輸入。")
    hex_ = manual_hexagram(throws)
    print_result(hex_, **nj)


HELP = """\
用法：
  python jinqian_gua.py random [seed] --at "YYYY-MM-DD HH:MM" --ask 求財
  python jinqian_gua.py manual <t1> ... <t6> --at "YYYY-MM-DD HH:MM" --ask 工作
  python jinqian_gua.py interactive --at "YYYY-MM-DD HH:MM" --ask 婚姻
  python jinqian_gua.py help

擲卦符號（每次 3 枚）：
  背=陽=3：背、陽、正、花、H、1、+
  字=陰=2：字、陰、反、T、0、-
  一背＝少陽、二背＝少陰、三背＝老陽（動）、三字＝老陰（動）
順序：自下而上（第 1 次＝初爻，第 6 次＝上爻）

納甲選項：
  --at    起卦當地時間 → 自動算月建（依節氣）、日干支（23 時起算次日）。強烈建議必帶。
  --tz    時區（小時，預設 8）
  --day / --month  手動覆蓋日干支／月建
  --ask   問事類型 → 用神、原忌神、用神綜合、應期（python najia.py list-questions）
"""


def main(argv: List[str]) -> None:
    if len(argv) < 2 or argv[1] in ("help", "-h", "--help"):
        print(HELP)
        return
    cmd, rest = argv[1], argv[2:]
    if cmd == "random":
        _cli_random(rest)
    elif cmd == "manual":
        _cli_manual(rest)
    elif cmd == "interactive":
        _cli_interactive(rest)
    else:
        print(f"未知指令：{cmd}\n")
        print(HELP)
        sys.exit(1)


if __name__ == "__main__":
    configure_stdout()
    main(sys.argv)
