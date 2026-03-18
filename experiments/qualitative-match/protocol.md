# Qualitative Match Experiment Protocol

**Started**: 2026-02-24
**Predecessor**: prediction-validation (binary, N=100, 51% result)

## What This Tests

The previous experiment forced Meihua into binary YES/NO and got coin-flip results. This experiment tests the actual claim: do hexagrams describe the **qualitative character** of situations better than random?

## Design

Three batches, tested separately due to different casting methods:

### Batch 1 (E01-E12)
- 12 upcoming events (Feb 27 - Mar 15, 2026)
- **Casting method**: Mechanical text-based (character count → trigram numbers)
- Control seed: `20260224`
- Each event gets 2 hexagram interpretations (real + control, blinded A/B)

### Batch 2 (E13-E32)
- 20 upcoming events (Mar 8 - Apr 12, 2026)
- **Casting method**: 取象法 (imagery-based — analyze event title semantics → map to bagua類象)
- Control seed: `20260305`, blinding seed: `20260306`
- Each event gets 2 hexagram interpretations (real + control, blinded A/B)
- Full skill output recorded for each real hexagram (取象理由, 體用, 策略, 爻位風險)

### Shared
- Interpretations written BEFORE events happen
- Blinded evaluation AFTER events resolve
- Wilcoxon signed-rank test on paired scores
- Batches analyzed separately, then combined if methods prove comparable

## Batch 1 Status Tracker

| Event | Cast | Interpreted | Resolved | Narrated | Scored |
|-------|------|------------|----------|----------|--------|
| E01 Apple Launch | Done | Done | Done (Mar 2-4) | Done | R=2, C=4 |
| E02 Lunar Eclipse | Done | Done | Done (Mar 3) | Done | R=5, C=1 ⭐ |
| E03 SpaceX Starship | Done | Done | Done (delayed) | Done | R=3, C=4 |
| E04 Tariff Challenge | Done | Done | Done (~Mar 7) | Done | R=2, C=4 |
| E05 Iran-US Crisis | Done | Done | Done (~Mar 10) | Done | R=3, C=1 |
| E06 Ukraine-Russia Talks | Done | Done | Done (~Mar 10) | Done | R=4, C=3 |
| E07 CL R16 Draw | Done | Done | Done (Feb 27) | Done | R=3, C=2 |
| E08 World Baseball Classic | Done | Done | Done (Mar 5-18) | Done | R=3, C=4 |
| E09 Oscars | Done | Done | Done (Mar 15) | Done | R=3, C=4 |
| E10 March Madness | Done | Done | Done (Mar 15) | Done | R=4, C=3 |
| E11 SOTU Aftermath | Done | Done | Done (Mar 3) | Done | R=4, C=1 ⭐ |
| E12 Blizzard/Polar Vortex | Done | Done | Done (~Mar 7) | Done | R=4, C=3 |

## Batch 2 Status Tracker

| Event | Domain | Cast | Interpreted | Resolved | Narrated | Scored |
|-------|--------|------|------------|----------|----------|--------|
| E13 F1 Australian GP | Sports | Done | Done | Done (Mar 8) | Done | R=4, C=2 |
| E14 Colombia Election | Politics | Done | Done | Done (Mar 8) | Done | R=2, C=4 |
| E15 WGA Awards | Culture | Done | Done | Done (Mar 8) | Done | R=3, C=4 |
| E16 Georgia Special Election | Politics | Done | Done | Done (Mar 10) | Done | R=3, C=3 |
| E17 Pixar Hoppers Box Office | Culture | Done | Done | Done (Mar 8) | Done | R=4, C=1 ⭐ |
| E18 NVIDIA GTC Keynote | Technology | Done | Done | Done (Mar 17) | Done | R=5, C=1 ⭐ |
| E19 FOMC Rate Decision | Economy | Done | Done | Pending (Mar 18) | - | - |
| E20 EU Council Summit | International | Done | Done | Pending (Mar 19-20) | - | - |
| E21 Project Hail Mary Premiere | Culture | Done | Done | Pending (Mar 20) | - | - |
| E22 World Indoor Athletics | Sports | Done | Done | Pending (Mar 21) | - | - |
| E23 South Australia Election | Politics | Done | Done | Pending (Mar 21) | - | - |
| E24 UN Fraud Summit | International | Done | Done | Done (Mar 16-17) | Done | R=3, C=4 |
| E25 Miami Open Tennis Final | Sports | Done | Done | Pending (Mar 29) | - | - |
| E26 F1 Japanese GP Suzuka | Sports | Done | Done | Pending (Mar 29) | - | - |
| E27 NCAA Championship Game | Sports | Done | Done | Pending (Apr 6) | - | - |
| E28 Masters Golf | Sports | Done | Done | Pending (Apr 12) | - | - |
| E29 Peru Presidential Election | Politics | Done | Done | Pending (Apr 12) | - | - |
| E30 Hungary Parliamentary Election | Politics | Done | Done | Pending (Apr 12) | - | - |
| E31 NASA Artemis II | Science/Space | Done | Done | Pending (~Apr 1) | - | - |
| E32 ISRO Gaganyaan Test | Science/Space | Done | Done | Pending (~Mar 30) | - | - |

## Workflow

1. **Phase 1**: Select events + cast hexagrams (DONE — both batches)
2. **Phase 2**: Write blinded interpretations (DONE — both batches)
3. **Phase 3**: Wait for events to resolve (Feb 27 - Apr 12)
4. **Phase 4**: Write factual narratives (blinded narrator, no hexagram access)
5. **Phase 5**: Score interpretations (blinded evaluator, 0-5 scale)
6. **Phase 6**: Unblind + statistical analysis (Wilcoxon signed-rank)

## Files

```
qualitative-match/
├── protocol.md                          (this file)
├── events/
│   └── event_registry.json              (12 batch 1 events)
├── hexagrams/
│   ├── casting_records.json             (batch 1: real + control + blinding)
│   ├── random_seed.txt                  (batch 1 seed: 20260224)
│   ├── casting_records_batch2.json      (batch 2: real + control + blinding)
│   ├── random_seed_batch2.txt           (batch 2 seed: 20260305)
│   └── generate_batch2.py              (batch 2 generation script)
├── interpretations/
│   ├── E01_A.md ... E12_B.md            (24 batch 1 blinded interpretations)
│   ├── E13_A.md ... E32_B.md            (40 batch 2 blinded interpretations)
│   ├── blinding_key.json                (batch 1 — SEALED until evaluation)
│   └── blinding_key_batch2.json         (batch 2 — SEALED until evaluation)
├── evaluations/                         (empty until Phase 5)
└── analysis/                            (empty until Phase 6)
```

## Key Dates

### Batch 1
- **Feb 27**: Champions League draw (first event!)
- **Mar 2-4**: Apple launch, Lunar eclipse, SOTU aftermath
- **Mar 5-11**: World Baseball Classic, Blizzard aftermath
- **Mar 7-9**: SpaceX Starship, Tariff challenges
- **Mar 10**: Iran-US crisis, Ukraine-Russia talks
- **Mar 15**: Oscars + March Madness Selection Sunday

### Batch 2
- **Mar 8**: F1 Australian GP, Colombia election, WGA Awards, Pixar Hoppers
- **Mar 10**: Georgia special election
- **Mar 16-17**: UN Fraud Summit
- **Mar 17-19**: NVIDIA GTC, FOMC rate decision, EU Council summit
- **Mar 20-21**: Project Hail Mary, World Indoor Athletics, South Australia election
- **Mar 29**: Miami Open final, F1 Japanese GP
- **Mar 30**: ISRO Gaganyaan test flight
- **Apr 1**: NASA Artemis II launch
- **Apr 6**: NCAA championship game
- **Apr 12**: Masters Golf, Peru election, Hungary election (last events)

## Interim Results (2026-03-18, 19/32 events scored)

| Metric | Batch 1 | Batch 2 (partial) | Combined |
|--------|---------|-------------------|----------|
| Events scored | 12/12 | 7/20 | 19/32 |
| Real mean | 3.33 | 3.43 | 3.37 |
| Control mean | 2.83 | 2.71 | 2.79 |
| Win record | 7-5 | 3-3-1T | 10-8-1T |
| Wilcoxon p | 0.261 | 0.250 | **0.139** |

See `evaluations/interim_report_2026-03-18.md` for full details.

## Batch 3 (E33-E62)
- 30 upcoming events (Apr - May 2026)
- **Casting method**: 取象法 via meihua-yishu skill (full skill invocation per event)
- Control seed: `20260318`
- Blinding seed: `20260319`
- Each event gets 2 hexagram interpretations (real + control, blinded A/B)
- Full skill output recorded

### Batch 3 Status Tracker

(To be populated after event selection and casting)

## Methodology Difference: Batch 1 vs Batch 2 vs Batch 3

| | Batch 1 | Batch 2 | Batch 3 |
|---|---------|---------|---------|
| Casting method | Mechanical (字數/字元數 → 數字) | 取象法 (LLM direct) | 取象法 (full skill invocation) |
| Script used | meihua_calc.py | LLM with bagua-wanwu.md | /meihua-yishu skill |
| Sample size | 12 events | 20 events | 30 events |
| Control seed | 20260224 | 20260305 | 20260318 |
| Extra data recorded | Word/char counts | 取象理由, 策略建議, 爻位風險 | Full skill output |
