# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This is **not a typical application repo** — it is the source of the `meihua-yishu` Claude Code Skill (Meihua Yishu / Plum Blossom I Ching divination). The "code" is mostly:

1. **`SKILL.md`** — the skill manifest and decision flow Claude follows when the skill activates (frontmatter + 500-line prompt). This is the canonical behavior spec; treat changes to it as user-facing changes.
2. **`references/*.md`** — knowledge base read on demand during a divination (64 hexagrams, line texts, bagua correspondences, strategy tables, classics in `references/classics/`).
3. **`scripts/*.py`** — three small calculators (Meihua casting, coin-toss casting, Najia / six-relatives annotation) plus tests. `fetch_classics.py` is a one-off downloader for ctext.org mirrors.

When a request changes divination behavior, decide whether it belongs in `SKILL.md` (decision flow / mandatory output format), a `references/*.md` (lookup data), or `scripts/*.py` (a computation). Most changes go in markdown, not code.

## Common commands

All from repo root. There are no build/lint steps and no third-party deps for the core scripts.

```bash
# Full test suite (131 tests across 6 risk tiers; runs in <20 ms)
python -m unittest discover -s scripts -p "test_*.py"

# Run a single tier
python -m unittest scripts.test_lunar_calendar
python -m unittest scripts.test_meihua_qigua.TestMeihuaQiguaByTime.test_shao_yong_plum_blossom_case

# Meihua casting CLI
python scripts/meihua_calc.py time                     # current time (Gregorian → lunar auto)
python scripts/meihua_calc.py gregorian 2024 1 18 14   # Gregorian + hour
python scripts/meihua_calc.py lunar 2023 12 8 14       # lunar directly
python scripts/meihua_calc.py num 6 8 9                # 2 or 3 numbers
python scripts/meihua_calc.py convert 2024 1 18        # Gregorian → lunar only

# Coin (六爻) casting CLI
python scripts/jinqian_gua.py random
python scripts/jinqian_gua.py random --day 甲子 --month 寅 --ask 求財   # adds Najia annotation
python scripts/jinqian_gua.py manual 背背字 字背字 背背背 字字字 背字背 字背背
python scripts/jinqian_gua.py interactive

# Refresh classics mirror from ctext.org (rarely needed)
python scripts/fetch_classics.py batch
```

The `experiments/prediction-validation/` subproject has its own `requirements.txt` and venv — it is unrelated to the skill itself (it tests whether the skill has predictive value on Polymarket). Don't touch unless asked.

## Architecture: how a divination actually flows

`SKILL.md` triggers on Chinese keywords (占卜, 起卦, 測字, 金錢卦, 六爻, 納甲, 世應, 用神, …) and English (meihua, plum blossom, I Ching). When it fires, Claude (not the user) must follow a fixed order:

1. **Branch on method first** — Meihua family (time/number/image/sound) vs. Coin-toss + Najia (六爻). If the user brought a specific question without choosing a method, the skill *requires* asking which to use before casting. Don't default to time-casting silently.
2. **Cast** — either via the LLM's own arithmetic (Meihua image-casting needs only `bagua-wanwu.md`) or by calling a script. Meihua time-casting **must** use the lunar calendar; `meihua_calc.py` has a built-in 1900–2099 lunar table so no external library is required.
3. **Interpret in a prescribed order** — line text (yaoci) first, then ti-yong, mutual hexagram, transformed hexagram, hexagram relationships, timing. Each step has a dedicated `references/*.md`.
4. **Output the strategy block** — this is mandatory and the format is fixed in `SKILL.md` (本卦 / 吉率 / 類型 / 策略 / 下一步 / 變卦路徑). The 6 strategy types (吸引子/排斥子/福地/困境/陷阱/一般 → 留/走/守/變/慎/觀) live in `HEXAGRAM_STRATEGY` in [meihua_calc.py:410](scripts/meihua_calc.py:410) and in `references/hexagram-strategy.md` — keep them in sync.

If you change the interpretation flow or the strategy output format, update **both** `SKILL.md` and the relevant `references/*.md` — the skill instructs Claude to read those files mid-conversation, so a contradiction will produce inconsistent readings.

## Code structure

- **`scripts/meihua_calc.py`** is the foundation module. It owns the canonical tables (`BAGUA`, `HEXAGRAMS`, `BINARY_TO_GUA`, `HEXAGRAM_STRATEGY`), the lunar conversion (`YEAR_INFOS` packed-bit table), and the casting helpers (`num_to_gua`, `apply_change`, `get_hu_gua`, `binary_to_gua_pair`).
- **`scripts/jinqian_gua.py`** and **`scripts/najia.py`** both `from meihua_calc import ...`. They reuse the same hexagram tables — don't duplicate.
- **Binary convention** for a 6-bit hexagram string: left 3 chars = upper trigram, right 3 chars = lower trigram. Position 1 (初爻) is the **rightmost** bit; `apply_change(binary, yao_position)` toggles `binary[6 - yao_position]`. The `test_coordinate_system.py` tier exists specifically to catch flips of this convention — re-run it after any change touching `apply_change`, `get_hu_gua`, or `binary_to_gua_pair`.
- **Remainder-zero rule**: `num_to_gua(n)` returns 8 when `n % 8 == 0`, `num_to_yao(n)` returns 6 when `n % 6 == 0`. Several historical cases depend on this — don't "fix" it to return 0.
- **Najia palace structure** (`PALACE_ORDER`, `HEX_TO_PALACE`, `SHI_POS`, `YING_POS`) encodes Jing Fang's eight-palace system and is cross-checked by the Tier 2 test against historical rules. Treat the table as authoritative; if a test fails after editing it, the table is wrong (not the test).

## Knowledge-base layout (`references/`)

The skill's decision tree in `SKILL.md` routes to specific files; keep filenames stable.

- Core lookup: `64gua.md`, `yaoci.md` (384 line texts), `zhouyi-zhuan.md`, `bagua-wanwu.md` (also contains 測字 / character-analysis rules at the bottom).
- Interpretation logic: `hexagram-relationships.md`, `hexagram-strategy.md` (**mandatory read every divination**), `yingqi-calc.md`.
- Specialized: `18-divinations.md` (Meihua specialized topics — marriage, illness, wealth, travel…), `liuyao-yongshen.md` (same 18 topics but for the coin/Najia system), `ying-guides.md` (environmental signs / 十應), `case-studies-expanded.md`, `case-studies-jinqian.md`.
- Coin system: `jinqian-gua.md` (Zhu Xi's rules for 0–6 changing lines), `najia-guide.md`, `najia-tables.md`.
- Modern bridges: `modern-references.md` (registers modern teaching books — concept frameworks only, no copyrighted text).
- Classics mirror: `references/classics/` — `classics-index.md` is the routing table by use-case, `classics-toc.md` is the chapter ID map, `eighteen-qa-cross-index.md` cross-references the two classics. Files under `zengshan-buyi/` and `buzheng-zhengzong/` are public-domain Qing-dynasty texts mirrored from ctext.org, each containing `【原文】` + `【現代語譯】` sections.

## Tests as documentation

The test files are organized as 6 "risk tiers" and are also the most readable spec of the historical rules being enforced:

- Tier 1 `test_coordinate_system.py` — binary ↔ hexagram conversion, changing-line index, mutual hex
- Tier 2 `test_palace_system.py` — Jing Fang's 8-palace attribution, world/response positions
- Tier 3 `test_najia_liuqin.py` — najia tables, six relatives, 5 canonical cases from 增刪卜易
- Tier 4 `test_yongshen_xunkong.py` — void days, yongshen, chong/he, fushen
- Tier 5 `test_lunar_calendar.py` — 200-year lunar conversion, year ganzhi, shichen
- Tier 6 `test_meihua_qigua.py` — end-to-end Meihua casting incl. Shao Yong's plum-blossom case

If you add a new historical rule, prefer adding a test that references its primary source (《增刪卜易》《卜筮正宗》《易學啟蒙》《梅花易數》) over inline comments.

## Ethics and tone (from `ETHICS.md`)

The skill is constrained to non-deterministic language ("傾向", "可能", never "一定"); must present both auspicious and inauspicious readings; will not predict death timing; redirects medical/legal/financial questions to professionals; and offers crisis resources if a querent indicates self-harm. Preserve these constraints when editing `SKILL.md`.

## License note

CC BY-NC-SA 4.0. Don't add code or text under incompatible licenses, and don't paste content from copyrighted modern books into `references/` — `modern-references.md` deliberately registers only the conceptual framework of those works.
