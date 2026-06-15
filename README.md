# 梅花易數 Meihua Yishu

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

[English](README.md) | [繁體中文](README.zh-TW.md)

Meihua Yishu (梅花易數 / Plum Blossom Numerology / Plum Blossom I Ching) is a traditional Chinese I Ching divination method, attributed to Shao Yong (邵雍) of the Song Dynasty. This project provides a professional Meihua divination system as an AI Skill for Claude Code.

> Also known as: 梅花易数 (Simplified Chinese), Mei Hua Yi Shu, Plum Blossom Oracle, 梅花心易

## Why Meihua Yishu?

### A Decision-Making Framework, Not Fortune-Telling

Unlike popular misconceptions about divination, Meihua Yishu is a structured thinking tool rooted in 3,000 years of Chinese philosophical wisdom:

| Misconception | Reality |
|---------------|---------|
| "Predicts the future" | Analyzes present conditions and likely trajectories |
| "Superstition" | Systematic framework based on pattern recognition |
| "Magic" | Philosophical method for examining situations from multiple angles |

### Benefits

🎯 Decision Clarity — When facing complex choices, the hexagram structure forces you to consider factors you might overlook

🔄 Multiple Perspectives — The Ti-Yong (体用) framework systematically examines self vs. environment, action vs. reaction

⏱️ Timing Awareness — The 應期 (Yingqi) system encourages thinking about *when* to act, not just *what* to do

🌊 Change Philosophy — Based on the I Ching principle that everything changes; helps accept uncertainty and plan adaptively

💭 Reflection Tool — The divination process creates space for introspection and deeper thinking about your situation

### Who Uses It?

- Entrepreneurs — For strategic timing and partnership decisions
- Individuals — For major life choices (career, relationships, relocation)
- Curious Minds — To explore Eastern philosophy and symbolic thinking
- Developers — To integrate traditional wisdom into AI applications

### The Meihua Advantage

Compared to other I Ching methods:
- Faster — No coins or yarrow stalks needed; cast from time, numbers, or observation
- More Intuitive — Trigram-based (8 symbols) rather than full hexagram memorization (64 symbols)
- Contextual — Ti-Yong analysis relates directly to your specific situation
- Practical — Clear auspicious/inauspicious framework with actionable insights

> *"The Yi does not predict fate — it reveals patterns. Understanding patterns empowers better choices."*

## Features

### Casting Methods
- Time-based Divination — Cast hexagrams using current or specified time
- Number-based Divination — Cast hexagrams using numbers
- Sound-based Divination — Cast using the count of sounds heard
- Color-based Divination — Cast based on colors corresponding to five elements
- Measurement-based Divination — Cast using object dimensions
- Direction-based Divination — Cast based on the direction of a person or object

### Interpretation Functions
- Ti-Yong Analysis — Interpret the relationship between Ti (体) and Yong (用) trigrams
- Tongguan Mediation — Analyze five-element bridging to mitigate克 (controlling) relationships
- 64 Hexagrams Interpretation — Detailed explanations of hexagram and line texts
- Changing Lines Derivation — Analyze the fortune of transformed hexagrams
- Seasonal Strength (卦氣) — Determine Ti trigram strength based on season
- Timing Prediction (應期) — Predict when events will manifest
- Strategy Guidance (策略建議) — Data-driven advice on whether to stay, leave, wait, or change (NEW!)

### Specialized Readings
- 18 Specific Readings — Marriage, illness, wealth, travel, and more
- Ten Responses (十應) — Environmental sign analysis
- Bagua Correspondences — Modern and traditional symbolic associations
- Character Analysis (測字) — Fortune telling by analyzing Chinese characters

### AI-Assisted Features
- Photo Analysis — Upload photos for AI to analyze environmental signs
- Environmental Sensing — Describe surrounding sounds, colors, people for enhanced readings

## Project Structure

```
meihua-yishu/
├── SKILL.md                      # Main skill documentation
├── ETHICS.md                     # Ethical guidelines (English)
├── ETHICS.zh-TW.md              # Ethical guidelines (繁體中文)
├── README.md                     # This file
├── README.zh-TW.md              # Traditional Chinese README
├── LICENSE                       # CC BY-NC-SA 4.0 License
├── references/
│   ├── 64gua.md                 # 64 Hexagrams detailed guide
│   ├── yaoci.md                 # 384 Line texts
│   ├── zhouyi-zhuan.md          # Tuan & Xiang commentaries
│   ├── bagua-wanwu.md           # Bagua correspondences + verses + character analysis (測字)
│   ├── hexagram-relationships.md # Hexagram relationships + statistical analysis + Tongguan
│   ├── hexagram-strategy.md     # Strategy guide (stay/leave/change decisions) - CORE!
│   ├── ying-guides.md           # Ten responses + external signs
│   ├── yingqi-calc.md           # Timing calculation guide
│   ├── 18-divinations.md        # 18 types of specific readings
│   └── case-studies-expanded.md # Classic divination cases (optional)
└── scripts/
    ├── meihua_calc.py           # Meihua casting (time/numbers/lunar conversion)
    ├── jinqian_gua.py           # Coin divination (六爻): simulates 3 coins × 6 throws
    ├── najia.py                 # Najia annotation (six relatives, world/response, void, yongshen)
    ├── fetch_classics.py        # Classics download helper
    └── test_*.py                # Unit tests (131 total, see "Test Suite" below)
```

## Usage

### As a Claude Code Skill

Easy way: Paste this URL in Claude Code and say "Please install this skill":
```
https://github.com/muyen/meihua-yishu
```

Manual way:
```bash
# Personal skills (works across all projects)
git clone https://github.com/muyen/meihua-yishu.git ~/.claude/skills/meihua-yishu

# Or for a specific project
git clone https://github.com/muyen/meihua-yishu.git .claude/skills/meihua-yishu
```

Once installed, mention divination keywords like "占卦", "起卦", or "meihua" — the skill will activate automatically.

### ChatGPT Custom GPT

1. Create a new GPT at https://chatgpt.com/gpts/editor
2. Copy the entire content of `SKILL.md` into the Instructions field (must be < 8000 characters)
3. Upload all 10 files from `references/` as Knowledge files
4. Set conversation starters: "幫我起卦", "占一卦", "測字"

### Google Gemini Gems

1. Create a new Gem at https://gemini.google.com/gems
2. Copy the entire content of `SKILL.md` into the Instructions field
3. Upload all 10 files from `references/` as Knowledge files (Gemini limit: 10 files)
4. Set suggested prompts: "幫我起卦", "占一卦", "測字"

### Using the Python Tool

```bash
# Cast hexagram using current time
python scripts/meihua_calc.py time

# Cast hexagram using two numbers
python scripts/meihua_calc.py num 6 8

# Cast hexagram using three numbers (third is changing line)
python scripts/meihua_calc.py num 6 8 3
```

Example output:

```
==================================================
📿 Meihua Yishu Divination Result
==================================================

【1. Calculation】
  Year: 10
  Month: 1
  Day: 17
  Hour: Hai (12)

【2. Primary Hexagram】
  #49: Ze Huo Ge (Revolution)
  Upper: Dui ☱
  Lower: Li ☲
  Binary: 011101
  Line 4 changing

【3. Ti-Yong Analysis】
  Ti Trigram: Li (lower) - Fire
  Yong Trigram: Dui (upper) - Metal
  Relationship: Ti controls Yong (Auspicious)

【4. Mutual Hexagram】
  Qian Wei Tian (Heaven over Heaven)

【5. Transformed Hexagram】
  #17: Ze Lei Sui (Following)
  Binary: 011001
==================================================
```

### Coin Divination (六爻) Simulation

```bash
# Computer simulates 3 coins × 6 throws
python scripts/jinqian_gua.py random

# Add day-ganzhi, month-zhi, and question type → auto-najia
# (six relatives, world/response, void, yongshen, timing)
python scripts/jinqian_gua.py random --day 甲子 --month 寅 --ask 求財

# Manually input 6 throw results
python scripts/jinqian_gua.py manual 背背字 字背字 背背背 字字字 背字背 字背背

# Interactive (one yao at a time)
python scripts/jinqian_gua.py interactive
```

Implements Zhu Xi's《易學啟蒙》0–6 changing-yao interpretation rules, special handling
for pure-yang/yin mutual hexagrams, and automatic palace-derived fushen (hidden god)
when the yongshen is absent from the primary hexagram.

## Test Suite

Core logic (casting / najia / six relatives / void / lunar conversion) is covered by
**134 unit tests** organized in 6 risk tiers:

| Tier | Topic | Tests |
|------|-------|-------|
| 1 | Coordinate system (binary, changing-line index, mutual hex) | 27 |
| 2 | Jing Fang's eight-palace attribution + world/response position | 16 |
| 3 | Najia tables + six relatives + 5 golden cases from 增刪卜易 | 16 |
| 4 | Void days + yongshen + chong/he + fushen | 29 |
| 5 | Lunar conversion (200 years) + year ganzhi + shichen | 24 |
| 6 | Meihua casting end-to-end + Shao Yong's plum-blossom case + strategy-table sync | 22 |

```bash
# Run the full suite (< 20 ms)
python -m unittest discover -s scripts -p "test_*.py"
```

All rules cross-checked against《增刪卜易》《卜筮正宗》《易學啟蒙》《梅花易數》
primary sources. The Jing Fang eight-palace structural test simultaneously validates
the `PALACE_ORDER` table, the `apply_change` logic, and the historical rule itself.

## Core Principles

### Yi = Change (易 = 變)

The fundamental principle of I Ching is change. The purpose of divination is not just to predict fortune, but to guide optimal action:

- Able to change = Auspicious (proactive adjustment, flow with circumstances)
- Unable to change = Inauspicious (stuck in place, missing opportunities)
- Staying in a bad position without changing = 0% success rate
- Proactive change = average 44% improvement in outcomes

Every divination must include strategy guidance — telling the querent what to do next.

### Early Heaven Bagua Numbers

Meihua Yishu uses Early Heaven Bagua Numbers:

| Trigram | Number | Element | Symbol |
|---------|--------|---------|--------|
| Qian (乾) | 1 | Metal | ☰ |
| Dui (兌) | 2 | Metal | ☱ |
| Li (離) | 3 | Fire | ☲ |
| Zhen (震) | 4 | Wood | ☳ |
| Xun (巽) | 5 | Wood | ☴ |
| Kan (坎) | 6 | Water | ☵ |
| Gen (艮) | 7 | Earth | ☶ |
| Kun (坤) | 8 | Earth | ☷ |

### Ti-Yong Theory

- Ti (体): The subject, self, the querent
- Yong (用): The object, matter, external environment
- Mutual Hexagram (互卦): The development process
- Transformed Hexagram (變卦): The final outcome

### Fortune Determination

| Situation | Fortune | Explanation |
|-----------|---------|-------------|
| Yong generates Ti | Very Auspicious | Gaining benefits, external assistance |
| Ti controls Yong | Auspicious | You control the situation, success likely |
| Ti-Yong in harmony | Auspicious | Same element, harmonious and smooth |
| Yong controls Ti | Inauspicious | Constrained by others, unfavorable |
| Ti generates Yong | Draining | Much effort, little return |

### Tongguan Mediation (通關化解)

When Ti and Yong are in a controlling relationship, a "bridging" element in the Mutual or Transformed hexagram can mitigate the inauspicious outcome:

| Controlling Relationship | Bridging Element |
|--------------------------|------------------|
| Metal controls Wood | Water |
| Wood controls Earth | Fire |
| Earth controls Water | Metal |
| Water controls Fire | Wood |
| Fire controls Metal | Earth |

## Divination Principles

1. No question, no divination — Don't divine without a specific question
2. No more than three times — Don't repeat divination for the same question more than three times
3. No movement, no divination — Don't divine without cause
4. Interpret with reason — Hexagrams must be interpreted in context

## References

- *Meihua Yishu (梅花易數)* — Shao Yong
- *Zhou Yi (I Ching / 周易)*
- *Introduction to I Ching Studies (易學啟蒙)*

## License

This work is licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).

You are free to:
- Share — copy and redistribute the material
- Adapt — remix, transform, and build upon the material

Under the following terms:
- Attribution — You must give appropriate credit
- NonCommercial — You may not use the material for commercial purposes
- ShareAlike — Derivatives must be distributed under the same license

Commercial Licensing: For commercial use, please contact muyen.lee@gmail.com

See [LICENSE](LICENSE) for details.

## Related Projects

- [Decoding I Ching](https://github.com/muyen/decoding-iching) — Data-driven research on I Ching patterns. Provides the 384-line database, hexagram strategy analysis, and statistical insights that complement Meihua divination.

## Contributing

Issues and Pull Requests are welcome!

---

☯️ The Yi has Taiji, which generates the Two Forms, which generate the Four Images, which generate the Eight Trigrams.
