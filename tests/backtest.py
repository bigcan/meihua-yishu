#!/usr/bin/env python3
"""
古例回測：拿原典卦例當標準答案，量引擎的判斷和書上差多少。

用法（放在技能的 tests/ 目錄下）：
    python tests/backtest.py            # 摘要
    python tests/backtest.py --miss     # 另列出判錯、未定、無判斷的卦例
    python tests/backtest.py --baseline # 與 tests/backtest_baseline.json 比較，數字退步則以非零狀態結束

量四件事：
  1. 裝卦一致率  —— 六親、地支、世應與書中卦盤逐爻相同
  2. 用神取對率  —— 書中明寫「某爻為用神」的卦例，引擎取的是否同一地支
  3. 吉凶一致率  —— 引擎「用神綜合」方向 vs 書中結果
  4. 應期命中率  —— 書中應驗之日的地支，是否在引擎的應期候選之內

開發組／保留組：有標註的卦例依編號分兩半。改規則時只看奇數編號（開發組）的錯例，
偶數編號（保留組）只在最後看數字，用來檢查規則是否只是在背開發組的答案。
`--miss` 預設只列開發組；`--miss-all` 才列全部（看了保留組的錯例，它就不再是保留組）。

注意：這量的是「與原典斷法的一致程度」，不是現實世界的準確率。
原典只收應驗之例；真實準確率只能靠驗卦紀錄累積。
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("MEIHUA_SKILL_ROOT") or os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import meihua_calc as mh  # noqa: E402
import najia as nj  # noqa: E402

ASK = {"世": "自身", "應": "對方", "父母": "父母", "兄弟": "兄弟",
       "子孫": "子女", "妻財": "求財", "官鬼": "工作"}


def direction(verdict) -> str:
    if not verdict:
        return "無判斷"
    return verdict.get("direction", "未定")


def is_dev(case_id: str) -> bool:
    return int(case_id[2:]) % 2 == 1


def run_liuyao(path: str):
    cases = json.load(open(path, encoding="utf-8"))["cases"]
    stat = {"n": len(cases), "layout_ok": 0, "ys_n": 0, "ys_ok": 0,
            "v_n": 0, "同向": 0, "相反": 0, "未定": 0, "無判斷": 0,
            "yq_n": 0, "yq_hit": 0, "yq_cands": 0,
            "dev_n": 0, "dev_ok": 0, "hold_n": 0, "hold_ok": 0, "all_ji": 0}
    miss = []
    for c in cases:
        h = nj.annotate(c["binary"], c["changing"], c["day"], c["month"])
        got = [[y.liuqin, y.zhi, "世" if y.is_shi else ("應" if y.is_ying else "")] for y in h.yaos]
        stat["layout_ok"] += got == c["layout"]
        if not c.get("outcome"):
            continue
        ctx = {"illness": c["illness"]} if c.get("illness") else None
        r = nj.find_yongshen(h, ASK[c["target"]], ctx)
        y = r.get("primary")
        if c.get("yongshen_zhi") and c["target"] not in ("世", "應"):
            stat["ys_n"] += 1
            stat["ys_ok"] += bool(y and y.zhi == c["yongshen_zhi"])
        v = r.get("verdict")
        d = direction(v)
        stat["v_n"] += 1
        stat["all_ji"] += c["outcome"] == "吉"
        key = d if d in ("未定", "無判斷") else ("同向" if d == c["outcome"] else "相反")
        stat[key] += 1
        grp = "dev" if is_dev(c["id"]) else "hold"
        stat[grp + "_n"] += 1
        stat[grp + "_ok"] += key == "同向"
        if key != "同向":
            miss.append(f'{"開" if grp == "dev" else "保"} {c["id"]} {c["month"]}月{c["day"]}日 {c["hex"]}'
                        f'{"之" + c["bian"] if c["bian"] else ""}｜{c["question"][:22]}｜書：{c["outcome"]}'
                        f'（{c["result_text"][:24]}）｜引擎：{d}〔{(v or {}).get("rule", "")}〕')
        days = [z[0] for z in c.get("yingqi", []) if z.endswith("日")]
        if days and y:
            tips = " ".join(nj.suggest_yingqi(h, y)[:-1])
            cands = set(re.findall(r"([子丑寅卯辰巳午未申酉戌亥])日", tips))
            stat["yq_n"] += 1
            stat["yq_hit"] += days[0] in cands
            stat["yq_cands"] += len(cands)
    return stat, miss


def run_meihua(path: str):
    cases = json.load(open(path, encoding="utf-8"))["cases"]
    ok, miss = 0, []
    for c in cases:
        r = mh._analyze_hexagram(c["upper"], c["lower"], c["dong"])
        s = r["體用總訣"]["分數"]
        d = "吉" if s >= 0.5 else ("凶" if s <= -0.5 else "未定")
        if d == c["outcome"]:
            ok += 1
        else:
            miss.append(f'{c["id"]} {c["name"]} {r["本卦"]["名稱"]}｜書：{c["outcome"]}（{c["result_text"]}）｜方向分 {s:+} → {d}')
    return {"n": len(cases), "同向": ok}, miss


def pct(a, b):
    return f"{a}/{b}（{100 * a / b:.0f}%）" if b else "—"


def main(argv):
    ly, ly_miss = run_liuyao(os.path.join(HERE, "gold_zengshan.json"))
    mhs, mh_miss = run_meihua(os.path.join(HERE, "gold_meihua.json"))
    print("══ 六爻：《增刪卜易》卦例 ══")
    print(f"  裝卦一致率   {pct(ly['layout_ok'], ly['n'])}")
    print(f"  用神取對率   {pct(ly['ys_ok'], ly['ys_n'])}　（書中明寫用神地支者）")
    print(f"  吉凶一致率   {pct(ly['同向'], ly['v_n'])}　相反 {ly['相反']}・未定 {ly['未定']}・無判斷 {ly['無判斷']}")
    print(f"    開發組 {pct(ly['dev_ok'], ly['dev_n'])}　保留組 {pct(ly['hold_ok'], ly['hold_n'])}　"
          f"（對照：一律猜吉 {pct(ly['all_ji'], ly['v_n'])}）")
    avg = ly["yq_cands"] / ly["yq_n"] if ly["yq_n"] else 0
    print(f"  應期命中率   {pct(ly['yq_hit'], ly['yq_n'])}　（平均每卦列 {avg:.1f} 個候選日支；隨機猜中約 {100 * avg / 12:.0f}%）")
    print("══ 梅花：原書占例 ══")
    print(f"  方向分一致率 {pct(mhs['同向'], mhs['n'])}")
    if "--miss" in argv or "--miss-all" in argv:
        shown = ly_miss if "--miss-all" in argv else [m for m in ly_miss if m.startswith("開")]
        print("\n── 六爻未同向" + ("" if "--miss-all" in argv else "（僅開發組）") + " ──")
        print("\n".join("  " + m for m in shown))
        print("\n── 梅花未同向 ──")
        print("\n".join("  " + m for m in mh_miss))
    summary = {"layout_ok": ly["layout_ok"], "ys_ok": ly["ys_ok"], "verdict_ok": ly["同向"],
               "verdict_wrong": ly["相反"], "holdout_ok": ly["hold_ok"],
               "yq_hit": ly["yq_hit"], "meihua_ok": mhs["同向"]}
    base_path = os.path.join(HERE, "backtest_baseline.json")
    if "--write-baseline" in argv:
        json.dump(summary, open(base_path, "w"), ensure_ascii=False, indent=1)
        print(f"\n已寫入基線：{base_path}")
    if "--baseline" in argv and os.path.exists(base_path):
        base = json.load(open(base_path))
        worse = [k for k in summary if k in base
                 and (summary[k] > base[k] if k == "verdict_wrong" else summary[k] < base[k])]
        print("\n與基線比較：" + ("無退步" if not worse else "退步項目 " + "、".join(worse)))
        return 1 if worse else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
