# Tibetan stream — seed tables for `bo/requirements.md` §6

Copy what applies into a Tibetan stream's `requirements.md` §6 when scaffolding
it. These are language facts, not text facts; the plan decides whether to adopt
each rule. Folded from the BCA Dalai-Lama track (`BCA-Daily-Practice-Plan-HHDL`),
where the generator got both of them wrong reliably.

---

## 1. Ending particles (རྫོགས་ཚིག / མཐའ་རྟགས)

When a sentence-final verb closes with one of the ten suffix letters, the
particle's initial consonant must equal the suffix letter:

| Suffix | Particle | Example |
|---|---|---|
| ག | གོ | བྱེད་གོ། |
| ང | ངོ | གཏོང་ངོ་། |
| ད | དོ | བགྱིད་དོ། |
| ན | ནོ | བྱིན་ནོ། |
| བ | བོ | འགྲུབ་བོ། |
| མ | མོ | བསམ་མོ། |
| ར | རོ | བགྱིར་རོ། |
| ལ | ལོ | བསྐྱལ་ལོ། |
| ས | སོ | བགྱིས་སོ། |

Wrong: `གཏོང་དོ།` (the ང suffix paired with the particle of a ད suffix) → `གཏོང་ངོ་།།`.

- A stem ending in the vowel-suffix འ takes འོ with contraction (དཀའོ།, མངའོ།).
- A stem with no suffix consonant takes འོ appended directly (སྡེའོ།, པོའོ།).
- If the plan adopts the double-shad rule: a sentence that closes with one of
  these particles ends with **།།**, never a single །.
- Exempt: the copulas/auxiliaries ཡིན་ མིན་ ཡོད་ མེད་, which close bare with a
  single shad; and every Fixed or Extracted section (liturgy, root verses,
  verbatim quotations), which is reproduced as attested.
- A mismatch is a **mechanical** error: correct it in place (like a bracket
  fix), do not regenerate and do not leave it.

---

## 2. Numbers in plan prose

Arabic digits are allowed only in `^block-id` anchors and file paths. In prose,
use Tibetan digits (title lines) or number words (citation phrases).

**Digits:** ༠ ༡ ༢ ༣ ༤ ༥ ༦ ༧ ༨ ༩ — combine positionally (35 → ༣༥, 134 → ༡༣༤).

**Cardinals 1–10:** གཅིག་ གཉིས་ གསུམ་ བཞི་ ལྔ་ དྲུག་ བདུན་ བརྒྱད་ དགུ་ བཅུ་ —
above ten, compose (11 → བཅུ་གཅིག་).

### Ordinals — compose, never guess

| N | Ordinal |
|---|---|
| 1 | དང་པོ། |
| 2–10 | cardinal + པ (གཉིས་པ། … བཅུ་པ།) |
| 11–19 | བཅུ་ + ones + པ — **except 15 → བཅོ་ལྔ་པ། and 18 → བཅོ་བརྒྱད་པ།** |
| 20, 30 … 90 | round number + པ (ཉི་ཤུ་པ། སུམ་ཅུ་པ། བཞི་བཅུ་པ། ལྔ་བཅུ་པ། དྲུག་ཅུ་པ། བདུན་ཅུ་པ། བརྒྱད་ཅུ་པ། དགུ་བཅུ་པ།) |
| 21–99 | decade prefix + ones + པ |
| 100 | བརྒྱ་པ། |
| 101–199 | བརྒྱ་དང་ + remainder ordinal (185 → བརྒྱ་དང་གྱ་ལྔ་པ།) |

Decade prefixes (they replace the cardinal root; the bco irregularity of 15/18
does not recur at 25/28 etc.):

| 20s | 30s | 40s | 50s | 60s | 70s | 80s | 90s |
|---|---|---|---|---|---|---|---|
| ཉེར་ | སོ་ | ཞེ་ | ང་ | རེ་ | དོན་ | གྱ་ | གོ་ |

Check: 35th → སོ་ལྔ་པ། ; 45th → ཞེ་ལྔ་པ། (adjacent decades, different prefixes —
the commonest guessing error).

### Citation-phrase pattern (example from the BCA track)

- Multi-verse: `ལེའུ་[chapter-ordinal]འི་ཚིགས་བཅད་[start-ordinal]་ནས་[end-ordinal]་བར་ཚིགས་བཅད་[count-cardinal]་གྱི་ཐོག་ལ་ཡིན།`
  — chapter 2, verses 35–37 → `ལེའུ་གཉིས་པའི་ཚིགས་བཅད་སོ་ལྔ་པ་ནས་སོ་བདུན་པ་བར་ཚིགས་བཅད་གསུམ་གྱི་ཐོག་ལ་ཡིན།`
- Single verse: `ལེའུ་[chapter-ordinal]འི་ཚིགས་བཅད་[verse-ordinal]་གྱི་ཐོག་ལ་ཡིན།`

The chapter-name table and any day → folder map are text facts: they belong in
the plan's own `About <plan-name>.md` / `requirements.md`, not here.
