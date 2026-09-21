---
name: format-commentary
description: >
  Format a commentary for the collection: repair OCR damage, structure the
  headings, normalise spacing and punctuation, and apply block IDs — producing a clean,
  navigable file that later skills can segment, cite, and transclude.

  Trigger on "format this commentary", "normalise this commentary", "fix the OCR in
  this file", "clean up the headings", "prepare this commentary".

  Runs BEFORE `segment-commentary`. This is where OCR repair belongs — the segmentation
  skills are forbidden from altering text, so anything not fixed here stays broken.
profile: any
supersedes:
  - 21-taras-rails/4-SYSTEM/Skills/format-commentary/SKILL.md
  - abhidhamma-rails/4-SYSTEM/Skills/format-commentary/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/format-commentary/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/format-chinese-commentary/SKILL.md
  - bodhisattvacharyavatara-rails/4-SYSTEM/Skills/ABC-Commentary-Formator/SKILL.md
---

> **Locations.** `$SKILL` is this skill's own directory. All other `$NAME`
> paths resolve per repo — see `rails/PROFILES.md`. Block ID and heading rules
> are in `rails/CONVENTIONS.md`; this skill implements them.

# Format and normalise a commentary

| Mode | Text | Use |
|---|---|---|
| 1 — Generic | Tibetan commentary | The default |
| 2 — Chinese | Chinese commentary | Different punctuation and segmentation conventions |
| 3 — Full pipeline | A commentary needing the complete treatment | Richest; developed on the Bodhicaryāvatāra commentaries |

**Mode 1 is the default.** Reach for mode 3 when a commentary needs more than
normalisation — it carries the full formatting pipeline, but it was developed against
one text's conventions, so read what it assumes before running it on an unrelated
commentary.

**This is the OCR-repair step, and the only one.** `segment-commentary` and
`add-block-ids` are both bound by a no-loss assertion and cannot fix a broken
character. If a commentary reaches them still damaged, the damage is permanent for
everything downstream that cites it. Do the repair here, and where a reading is
genuinely uncertain, leave an `[Ed: …]` note rather than a silent guess.

---

## Mode 1 — Generic Tibetan commentary

**Role:** Expert Editor in Tibetan Buddhist Literature, Text Reconstruction, and Markdown Formatting.

**Task:** Process Tibetan commentaries by fixing OCR errors, structuring the text with specific hierarchical logic, and applying precise metadata via Obsidian block references.

**1. OCR Cleanup & Text Reconstruction**

- **No Deletions:** Strictly preserve the entire source text. Do not omit any analysis or citations.
    
- **Grammar Fixes:** Reconstruct Tibetan syllables. Fix broken words caused by OCR (e.g., join vowels to bases, ensure correct tsheg placement).
    
- **Latin Prefix Removal:** Actively identify and remove stray Latin characters (e.g., 'm', 'g', 'b', 't') that were incorrectly prefixed to Tibetan words during the OCR process (e.g., change "mཚན་མ་" to "མཚན་མ་").
    
- **Continuous Flow:** Remove arbitrary line numbers within sentences to form smooth, logically grouped text.
    
- **Continuous Flow:** Remove arbitrary line breaks within sentences to form smooth, logically grouped text.

**2. Heading Structure (མགོ་བརྗོད་རྩ་དོན)**

- **Level 1 (#):** Main Title. No numerical prefix. No block ID.
    
- **Level 2 (##):** The first section immediately following the title must start with the numeral 0. (e.g., `## 0. མཆོད་བརྗོད།`). Subsequent sections use 1., 2., etc. No block ID.
    
- **Level 3 (###):** Use numerical prefixes (e.g., `### 1.1 ...`). No block ID.
    
- **Level 4 (####):** No numerical prefixes. No block ID.
    
- **Spacing:** Leave exactly one blank line before and after every heading.
    

**3. Paragraph & Verse Formatting**

- **Logical Blocks (Granularity):** Break long prose sections into very short, discrete paragraphs (ideally 1–2 sentences). Blocks must be kept short to ensure they are highly optimized for referencing. If a paragraph exceeds 3-4 lines of Tibetan text, you must find a logical break point to split it.
    
- **Verses (ཚིགས་བཅད):** Count and separate blocks by each independent stanza. An independent stanza is defined by its context. Keep verse lines together within a single stanza, but do not group multiple independent stanzas into the same block.
    
- **Quotes (ལུང་འདྲེན):** Place source references (e.g., སྡུད་པ་ལས།) on their own separate line above the quote. Place concluding remarks (e.g., ཞེས་སོ། །) on their own separate line below the quote.
    

**4. Obsidian Block IDs**

- **Placement:** Add a unique Obsidian block ID at the end of every discrete text block (short paragraphs, independent verse stanzas, standalone citation lines).
    
- **ID Formatting:**
    
    - Simple Sections: Use a 2-segment format (e.g., `^0-1`, `^1-5`).
        
    - Nested Sections: Use a 3-segment format (e.g., `^1-1-1`, `^2-2-45`).
        
- **ID Limit:** IDs must not exceed 3 segments (flatten if necessary).
    
- **Sequence Restart:** Restart the block numbering sequence (the final segment) under every new Level 2 (##) or Level 3 (###) heading.
    
- **Restriction:** Do NOT add block IDs to any heading levels (#, ##, ###, ####).
    

**5. Output Protocol**

- Provide the final cleaned and formatted Tibetan text entirely within a single Markdown file block.
    
- Use LaTeX-style syntax for any mathematical or scientific notation (e.g., $formula$).

---

## Mode 2 — Chinese commentary

### 目的

此技能定義了在 `$COMMENTARIES/` 文件夾中，對《入菩薩行論》中文註釋進行格式化、結構化和標準化的標準程序。它將傳統中文科判映射到 Markdown 標題層次結構中，將長篇散文分解為高度細粒度的段落，嵌入根頌，應用精確的 Obsidian 區塊識別碼，並實施穩健的批處理協議以處理長文本。

---

### 核心原則

1.  **嚴格保留**: 不刪除、不總結、不更改任何註釋文本。保留原始措辭，包括傳統科判標籤（例如 `甲一`、`乙二`、`丙三`）。
2.  **段落細粒度化**: 將長篇散文部分分解為非常簡短、獨立的段落（理想情況下為 1-3 句，不超過 3-4 行中文文本）。這對於精確的區塊引用至關重要。
3.  **傳統科判映射**: 將分層的中文科判標籤映射到 Markdown 標題層次結構，最高到四級標題 (`####`)。
4.  **根頌嵌入**: 在該頌詞的註釋之前，立即插入一個指向根文本文件中匹配根頌的嵌入連結。
5.  **Obsidian 區塊識別碼**: 在每個獨立的文本區塊（段落、頌詞、獨立列表項）末尾應用順序、唯一的區塊識別碼，並在每個標題下重新開始計數。
6.  **分批處理**: 由於註釋文本極長，必須以大約 **100-150 行文本**（或約 3000-5000 字）的順序批次（塊）進行處理文本，並維護一個狀態區塊以確保連續性。

---

### 1. 標題結構與科判對照

傳統中文註釋使用廣泛的分層科判（以天干：甲、乙、丙、丁...；地支：子、丑、寅、卯...；或中文數字：一、二、三... 作為前綴）來組織其分析。這些必須映射到 Markdown 標題樹中：

-   **一級標題 (`#`)**: 主書名。僅在文件頂部（位於前置元數據下方）使用一次。無區塊識別碼。
-   **二級標題 (`##`)**: 品。格式：`## N. [品名] ^N-0`（例如：`## 1. 第一品 讚菩提心功德品 ^1-0`）。
-   **三級標題 (`###`)**: 主要結構劃分（通常是 `甲` 級）。格式：`### N.M [劃分標題] ^N-M-0`（例如：`### 1.1 甲一、釋題 ^1-1-0`）。
-   **四級標題 (`####`)**: 次級劃分（通常是 `乙` 或 `丙` 級）。格式：`#### N.M.P [次級劃分標題] ^N-M-P-0`（例如：`#### 1.1.1 乙一、譯文皈敬 ^1-1-1-0`）。
-   **更細粒度的劃分**: 對於更深層次（例如 `丁`、`戊`、`己`、`子`、`丑` 等），請勿使用深於 `####` 的標題（五級標題 `#####` 受限制）。相反，將它們格式化為標準段落中的粗體文本，後跟一個區塊識別碼（例如：`**丁一、所為義。** 由於稱揚殊勝皈境功德... ^1-1-5`）。

#### 格式規則:
-   每個標題前後必須留一個空行。
-   標題的識別碼格式始終以 `-0` 結尾（為標題保留）。
-   請勿在標題行末尾使用插入符號 `^` 添加區塊識別碼；而應將其內聯寫在標題文本的末尾（例如：`### 1.1 甲一、釋題 ^1-1-0`）。

---

### 2. 段落與頌詞格式

-   **散文粒度**: 長段落必須在邏輯斷點處（例如，論證的過渡、新的次級論點或引文之前/之後）進行拆分。保持段落簡短（1-2 句，最多 3-4 行），以優化其引用。
-   **根頌嵌入**: 每當引入一個根頌時，插入一個指向根文本文件的嵌入連結。
    -   格式：`![[$SOURCE_TEXTS/sk-dev.md#^1-1]]`（其中 `sk-dev.md` 是前置元數據中聲明的根文本，`^1-1` 是匹配的頌詞識別碼）。
-   **中文頌詞翻譯**: 如果註釋包含根頌的中文翻譯（通常是四行詩節），請將其格式化為獨立的區塊，每行頌詞單獨成行：
    ```markdown
    為己一切生中備諮詢，  
    亦為利他與我同類機，  
    遵依正士智者之所許，  
    入菩薩行論釋今當作。 ^1-10
    ```
    注意：在每個行末使用兩個空格來表示區塊內的換行，並將區塊識別碼放在最後一行的末尾。

---

### 3. Obsidian 區塊識別碼規範

-   **位置**: 在每個獨立的文本區塊（段落、頌詞、獨立列表項）的末尾添加一個唯一的區塊識別碼。
-   **識別碼格式**:
    -   章節級區塊：`^N-V`（其中 `N` 是章節號，`V` 是從 1 開始的順序計數器）。
    -   分段級區塊：`^N-S-V`（其中 `S` 是分段號）。
    -   為避免複雜性，**始終優先使用扁平的 2 段或 3 段格式**（例如：`^1-1`、`^1-2` 或 `^1-1-1`、`^1-1-2`）。
-   **序列重啟**: 順序計數器 (`V`) 必須在每個新的二級標題 (`##`) 或三級標題 (`###`) 下重新從 `1` 開始。
-   **標題上不使用插入符號**: 請勿在標題行上使用帶有插入符號 `^` 的區塊識別碼。標題使用內聯的 `-0` 格式（例如：`### 1.1 甲一、釋題 ^1-1-0`）。

---

### 4. 分批處理協議

由於中文註釋文本極長，必須以大約 **100-150 行文本**（或約 3000-5000 字）的順序批次（塊）進行處理。

為確保在不同運行之間保持結構一致性，代理必須遵循以下協議：

#### 步驟 1: 識別和拆分
1.  讀取原始文本文件並識別自然邊界（例如，章節末尾、主要 `甲` 部分的末尾）。
2.  將文件拆分為順序批次。如有需要，將原始批次保存在 `$WORK/` 中。

#### 步驟 2: 讀取狀態
在處理新批次之前，從上一個已處理文件的末尾或當前會話上下文中讀取 **狀態區塊**。狀態區塊跟踪：
-   `current_chapter`（章節號，例如 `1`）
-   `current_section`（分段號，例如 `1.1`）
-   `current_subsection`（次級分段號，例如 `1.1.1` 或 `none`）
-   `block_counter`（順序區塊計數器，例如 `45`）

#### 步驟 3: 格式化批次
處理批次，應用所有格式化、科判映射和區塊識別碼規則。確保：
-   如果遇到新標題，將 `block_counter` 重置為 `1`（或適當的子計數器）。
-   每個格式化的段落/頌詞都遞增 `block_counter`。

#### 步驟 4: 寫入和追加
將格式化的文本追加到 `$COMMENTARIES/` 中的目標文件。

#### 步驟 5: 寫入狀態區塊
在已處理批次的末尾，將更新後的狀態區塊作為 HTML 注釋寫入，以便下次運行可以讀取它：
```markdown
<!-- BATCH_STATE
current_chapter: 1
current_section: 1.2
current_subsection: 1.2.1
block_counter: 18
-->
```

---

### 5. 示例

#### 原始中文註釋輸入:
```text
入菩薩行論廣解卷一
極尊正士諸具大悲心者足下恭敬頂禮。
誰之智慧盡除諸罪，相好功德熾然四身，輪超法界際，大悲流露六十支分韻音，無垢光明普照無邊諸眾生，任運成辦，恒常無間，善能破除無邊眾生愚癡諸黑暗，於諸能仁自在上師大士聖妙吉祥足前，我今恭敬禮。
為己一切生中備諮詢，亦為利他與我同類機，遵依正士智者之所許，入菩薩行論釋今當作。自見取執絹網所繫縛，謂言欲證小乘菩提果，不須證入甚深真如性，願捨諸顛倒說而諦聽。
其所造《入菩薩行論》分四：甲一、釋題；甲二、皈敬；甲三、正義；甲四、結義。今初：
梵語有四種，此是桑支達語也。此論題名「菩提」，藏語降曲；「薩埵」，藏語「生巴」；「雜雅」，藏语「覺巴」；阿瓦打[冒-目+阿]藏語「[覺/勿]巴。」
```

#### 格式化輸出:
```markdown
---
title: 入菩薩行論廣解
author: 賈曹傑 (Gyaltsab Je)
translator: 隆蓮法師 (Longlian)
language: Chinese
file_type: commentary
lang_tag: zh
verse_id_format: verse
registered_id: gyaltsab-je
root_text: $SOURCE_TEXTS/sk-dev.md
covers_verses: 1-1–10-58
source_description: "隆蓮法師譯《入菩薩行論廣解》。"
---

## 入菩薩行論廣解

### 0. Introduction ^0-0

入菩薩行論廣解  
寂天菩薩造頌　傑操大師註解　隆蓮法師譯 ^0-1

極尊正士諸具大悲心者足下恭敬頂禮。 ^0-2

誰之智慧盡除諸罪，相好功德熾然四身，輪超法界際，大悲流露六十支分韻音，無垢光明普照無邊諸眾生，任運成辦，恒常無間，善能破除無邊眾生愚癡諸黑暗，於諸能仁自在上師大士聖妙吉祥足前，我今恭敬禮。 ^0-3

為己一切生中備諮詢，  
亦為利他與我同類機，  
遵依正士智者之所許，  
入菩薩行論釋今當作。 ^0-4

自見取執絹網所繫縛，謂言欲證小乘菩提果，不須證入甚深真如性，願捨諸顛倒說而諦聽。 ^0-5

#### 0.1 總綱科判 ^0-1-0

其所造《入菩薩行論》分四：甲一、釋題；甲二、皈敬；甲三、正義；甲四、結義。今初： ^0-1-1

##### 0.1.1 甲一、釋題 ^0-1-1-0

梵語有四種，此是桑支達語也。此論題名「菩提」，藏語降曲；「薩埵」，藏語「生巴」；「雜雅」，藏语「覺巴」；阿瓦打[冒-目+阿]藏語「[覺/勿]巴。」 ^0-1-1-1

<!-- BATCH_STATE
current_chapter: 0
current_section: 0.1
current_subsection: 0.1.1
block_counter: 1
-->
```

---

### 6. 品質檢查表

-   [ ] 文件頂部存在包含所有必需字段的前置元數據區塊。
-   [ ] 標題嚴格按照 `## N. 標題 ^N-0`（或 `### N.M 標題 ^N-M-0`）的格式。
-   [ ] 標題行末尾沒有插入符號 `^`。
-   [ ] 所有散文部分都已拆分為短段落（最多 3-4 行）。
-   [ ] 根頌嵌入已正確插入，格式為 `![[$SOURCE_TEXTS/sk-dev.md#^N-V]]`。
-   [ ] 區塊識別碼是順序的、唯一的，並在每個標題下從 1 重新開始。
-   [ ] 狀態區塊已追加到批次末尾。
-   [ ] 沒有遺漏或總結任何文本、註釋或科判標籤。

---

## Mode 3 — Full formatting pipeline

### What this does

This skill formats a segmented Tibetan commentary file (in `$WORK/`) that has a companion **outline file** -- a separate bullet-list ས་བཅད (bare topical outline) whose entries carry `^TOC-N-N-N...` anchors, one dash-separated number per nesting depth. That outline is the ground truth for heading structure; the commentary file's own headings are matched against it rather than inferred purely from local context, because a commentary's headings are often bare, wrongly leveled, or formatted as bullets instead of real markdown headings.

Three tasks, each independently useful, normally run in this order:

1. **Heading tagging** (`scripts/align_headings.py`) -- aligns the commentary's heading-shaped lines against the outline and rewrites each with the correct `#` depth.
2. **Segmentation** (`scripts/find_long_segments.py`) -- in report mode (default), lists long body segments that look like two-or-more merged thoughts; with `--apply`, actually splits them at the vault's own sentence-break convention.
3. **Obsidian Block IDs** (`scripts/tag_heading_block_ids.py` then `scripts/tag_body_block_ids.py`) -- stamps two independent id sequences, one for headings and one for body text.

Run 1 before 3 (Block IDs are computed from heading depth/position, so headings must already be correctly leveled). Task 2 in **report mode** can run any time after 1, independently of 3 -- it only reads. Task 2 in **`--apply` mode** changes block boundaries, so it must run BEFORE Task 3b (body Block IDs) -- any split segment loses its old id (a single id can't identify two new pieces), and 3b is what assigns fresh ids to the pieces. If you run `--apply` on a file that's already been through Task 3, re-run 3b afterward before delivering.

### Task 1: Heading tagging (`align_headings.py`)

#### Why alignment, not just counting number-of-segments

A companion outline entry's `^TOC-1-1-2-2` tells you its depth (4 segments -> heading level 5) but the commentary's own heading TEXT differs slightly from the outline's -- the commentary adds an ordinal word (དང་པོ་/གཉིས་པ་/གསུམ་པ་/...) that the bare outline omits, and occasional wording drifts (e.g. outline `བོད་སྐད་ལྟར་སྨོས་པ` vs. commentary `བོད་སྐད་དུ་སྨོས་པ`). So matching is done by normalized-title similarity (ordinal-stripped, punctuation-stripped), using a Needleman-Wunsch global alignment over BOTH sequences in order -- this correctly handles:

- Outline nodes with **no heading of their own** in the body (the text goes straight from a parent heading into that parent's own children without ever stating the intermediate node -- e.g. "དགོས་པ་དངོས" is implied but never itself headed). These are expected gaps, not errors -- never fabricate heading text for them.
- Body headings with **no outline match** (hand-added `## N. Chapter N` title lines the outline doesn't track, or headings whose wording drifted too far to match confidently). Leave these completely untouched.
- Existing headings that are **already correctly leveled** -- these end up unchanged (idempotent).

#### What counts as a heading-candidate line

Any of: an existing markdown heading (`#` through `#############`), a `* **bold**` bullet, or a bare `**bold**` line. This vault's commentaries use bullets/bold as an ad-hoc heading substitute before this skill fixes them.

#### The glued-heading data quirk

Occasionally two headings end up on one physical line with a stray outline-number code stuck in the middle, e.g.:

```
**གསུམ་པ་ཕན་ཡོན་དཔེའི་སྒོ་ནས་བསྟན་པ།1.2.2.1.1.1.2.1.3.1 དང་པོ། གསེར་འགྱུར་...**
```

`align_headings.py` detects a 3+-segment dot-number glued directly onto non-whitespace (no space before it -- that's the signal it's stuck on, not just mentioned in prose) and splits it into two separate heading lines before alignment, so both halves get tagged at their correct (different) depths.

#### Running it

```bash
python3 scripts/align_headings.py "<path-to-staged-file>" "<path-to-outline-file>"
```

Writes a `.BACKUP-YYYYMMDD-HHMMSS.md` next to the target before overwriting in place. Check the printed summary:

- **matched** should account for the large majority of heading-candidates.
- **low-confidence matches (<0.8)** -- skim every one of these; they're usually correct (wording drift) but occasionally a genuine mismatch. Never silently trust a run with many low-confidence matches on a new file family without spot-checking a handful of them against the source.
- **outline entries with no matching heading** and **body candidates with no outline match** are both normal in nonzero numbers (see above) -- only worry if the counts look wildly out of proportion to the file's length.

#### Verification: no heading level should jump by more than 1

After tagging, walk the headings in order and flag any place level increases by more than 1 step (e.g. level 5 straight to level 7). A jump of exactly the size of one missing outline node is expected and fine (see above); a jump you can't explain by a genuinely absent outline node is worth asking the user about rather than assuming. A quick way to check:

```python
prev = None
for lineno, level, text in headings:  # parsed the same way align_headings.py does
    if prev and level > prev[1] + 1:
        print(prev, "->", (lineno, level, text))
    prev = (lineno, level, text)
```

If the user has hand-corrected specific headings' levels since your last check, re-stage the file and re-run this check on the CURRENT content before reporting -- this file family is often being edited live by the user in parallel with your work.

#### Related manual cleanups (not automated by this skill, but common asks on the same files)

These aren't part of `align_headings.py` but come up on the same file family and are worth knowing:

- **Removing hand-added numbered chapter-title lines** (e.g. `### 2. ལེའུ་གཉིས་པ། སྡིག་པ་བཤགས་པ། ^2-0`) if the user no longer wants them, once the outline-based headings already carry that structure. Do this as a simple line-removal pass (also delete one of the two blank lines left dangling around each removed line, to avoid a double blank), keyed on a regex like `^#+\s*\d+\.\s*ལེའུ`.
- **Inserting a blank line between two headings that are directly adjacent** (no blank line between them) -- this vault's convention wants one blank line between every pair of heading lines, matching example: `####### **...**` immediately followed by `######## **...**` should get a blank line inserted between them. Simple line-scan: after any heading line, if the very next line is also a heading line, insert a blank line.

### Task 2: Segmentation (`find_long_segments.py`)

#### What "this vault's segmentation convention" actually is

Reverse-engineered empirically from `$WORK/BCAC20_NKW_bo_segmented_tagged.md` (the reference example for this convention): body segments in this file family are **not** "one sentence per block." In a sample of 1402 prose blocks in that file, ~84% legitimately contain more than one double-shad-terminated sentence merged into one coherent explanatory unit, with a median length around 420 characters. The file's own practical ceiling sits around 800 characters -- blocks at or above that are rare (~10% of prose blocks) and are exactly the ones worth a second look or a split. Two hypotheses were tested and rejected before landing on this: "split at every ordinal word (དང་པོ་/གཉིས་པ་/...)" only matched 57% of real block starts (43% of ordinals appear mid-block, continuing a thought rather than opening a new one), and "one sentence per block" is flatly contradicted by the 84% figure above. So: **don't lower `--min-length` "to be thorough"** -- that fights the vault's actual convention and over-splits perfectly normal blocks. The split point itself, when a block genuinely is too long, is the same signal the vault's own text uses at every real paragraph break: a double shad (the normal Tibetan full stop) with more text after it before the segment's end, chosen as the one nearest the exact midpoint among those falling within the middle 65% of the segment (between 20% and 85% of its length, so a split is never forced right at an edge).

**Watch for the double-shad spacing convention differing by commentary/edition.** BCAC20_NKW spaces the two `།` characters apart (`། །`, ~4164 occurrences, essentially the only form used); `BCAC16_PK` (Pema Karpo) glues them with no space (`།།`, 693 occurrences vs. only 4 spaced ones) -- a different digitization convention, not an error in either file. `find_long_segments.py`'s break pattern matches either spacing (`།\s*།`) so this doesn't need per-file configuration, but if you're extending or reimplementing this logic, check both counts on a new file before assuming one convention -- a script hardcoded to only the spaced form would find almost no break points at all on a glued-convention file (this happened during BCAC16_PK's first `--apply` run: 1 giant 255k-character segment split into only 4 pieces before the fix, 302 sensible pieces after).

#### Two modes

**Report mode (default, no `--apply`)** -- never edits the file. Lists candidates for a human, or for a follow-up `--apply` run, to review.

```bash
python3 scripts/find_long_segments.py "<path-to-staged-file>" --min-length 800 --out report.md
```

Deliver `report.md` to the user (it's a markdown table -- send it as a file, don't try to paste an 800+-row table into chat). Segments with a clean break are strong candidates; segments without one still get listed (long but no obvious midpoint) since they're worth a human look even though the split point isn't mechanically obvious -- never invent a split point for these without a clear sentence boundary to point to.

**Apply mode (`--apply`)** -- actually re-segments the file. For every prose body segment at or above `--min-length`, recursively finds the best interior double-shad break, splits there, and repeats on each resulting half -- so a block over-merged from three sentences becomes three blocks in one pass, not just two. A half that's still too long but has no further interior double-shad to split at is left as one piece (the same "long segment without an obvious break point" case report mode surfaces) -- this never invents a split point without a genuine sentence-boundary anchor.

```bash
python3 scripts/find_long_segments.py "<path-to-staged-file>" --min-length 800 --apply
```

`--apply` is meant for two situations:

- **Cleaning up a handful of over-long segments** in an already-segmented file (the original use case) -- most calls will change very few blocks.
- **Segmenting a RAW or barely-segmented commentary from scratch** -- point it at a file where whole chapters sit in one giant paragraph, and it recursively cuts every such blob down to this vault's normal block granularity using the exact same break rule throughout. This is what makes Task 2 usable on **other commentary texts**, not just as a QC pass on the one it was reverse-engineered from. When asked to segment a new/raw commentary "the same way as `BCAC20_NKW_bo_segmented_tagged`," this is the tool -- there is no separate script for that request.

A segment's existing Obsidian Block ID (if any) is **dropped** when that segment is split -- one id can't identify two new pieces, and every piece needs its own fresh id. **Run Task 3b (`tag_body_block_ids.py`) again after any `--apply` run that reports changes**, to (re)stamp ids on the new block boundaries; it's explicitly designed to assign fresh ids to anchor-less segments, whatever caused them to lack one. A segment that was NOT split keeps its existing id untouched. Headings, frontmatter, lone image-embed lines, and verse/stanza quote blocks (consecutive `>` lines) are never touched or counted in either mode -- splitting a quoted verse doesn't make sense, and this task is scoped to prose only.

Writes a `.BACKUP-YYYYMMDD-HHMMSS.md` before overwriting, matching the other scripts' convention. Report-mode output is unaffected by the `--apply` code path -- running without `--apply` behaves exactly as before this capability was added.

### Task 3: Obsidian Block IDs -- two separate sequences

This vault's `^label-N` anchors are called **Obsidian Block IDs**. This skill stamps TWO independent sequences that must never be merged or cross-numbered:

#### 3a. Heading Block IDs (`tag_heading_block_ids.py`)

Tree-shaped, one id per heading, encoding its position in the outline:

- Every id is a path of 1-based sibling-position numbers (one segment per level below the first level-2 heading), always ending in a constant `-0`. The count of `-N-` segments in the id always equals `heading level - 1` -- e.g. `^I-1-1-2-0` is 4 segments -> level 5.
- The level-2 (`##`) headings get special root labels: the FIRST one is `"I"`; every one after that is a plain arabic number starting at 1 (2nd level-2 heading -> `"1"`, 3rd -> `"2"`, ...). This matches the existing hand-set convention in this file family (roman numeral for the intro, arabic for the rest).
- Every other heading gets its 1-based sibling index among headings sharing the same nearest-shallower-level ancestor, appended to that ancestor's path (ancestor's own trailing `-0` dropped), plus its own trailing `-0`.
- **Skipped levels** (outline has an implicit parent that never got its own heading -- see Task 1) are padded with an implicit sibling index of 1 for the missing level, so id depth still matches heading level across the gap. Don't try to "fix" this by inventing heading text.

```bash
python3 scripts/tag_heading_block_ids.py "<path-to-staged-file>"
```

Check the printed depth-mismatch and duplicate-id counts -- both must be 0. Validate against any pre-existing hand-set anchors in the file (e.g. `^I-0`, `^1-0`) if present -- the algorithm should reproduce them exactly; if it doesn't, something about this file's root-labeling doesn't match the "I / 1 / 2 / ..." convention and you should ask the user rather than force it.

#### 3b. Body-text Block IDs (`tag_body_block_ids.py`)

Flat, restarts only at level-2 headings:

- `<label>` is inherited from the nearest preceding level-2 heading's OWN id (its label, with trailing `-0` dropped) -- so it's always `"I"`, `"1"`, `"2"`, etc., matching 3a's root labels.
- `<n>` restarts at 1 right after that level-2 heading and counts every body segment (paragraph or verse-stanza) continuously -- across every chapter and sub-heading under that ONE level-2 heading -- until the next level-2 heading. **This does not restart at chapter boundaries or at any heading deeper than level 2** -- that's the key difference from this vault's other, older commentary-formatting skill.
- Content before the very first level-2 heading gets label `"0"`.
- **Every non-heading, non-frontmatter, non-lone-embed-line block gets an id, whether or not it already had one.** A body block that currently has NO anchor at all (e.g. a paragraph a human split off from a bigger block by hand, leaving the new fragment un-anchored) must still be tagged -- don't just renumber existing anchors and skip blocks that lack one. This was a real bug once: silently skipping anchor-less blocks left segments permanently untagged.
- Frontmatter (the `---`-delimited YAML block at the very top) and lone image-embed lines (`![[...]]`, referencing another file's own block) are never touched or counted.
- A heading line is always its own block boundary even with no blank line separating it from adjacent text (e.g. YAML frontmatter's closing `---` immediately followed by the `# document title` heading with no blank line between them) -- grouping blocks purely by blank lines would merge the heading into the frontmatter's "block" and corrupt it. `tag_body_block_ids.py` handles this; if you ever write a variant of this logic yourself, keep this in mind.

```bash
python3 scripts/tag_body_block_ids.py "<path-to-staged-file>"
```

Check the printed per-label range (`label X: 1..N`) -- ranges should be gap-free and start at 1 for each label. The "segments that previously had NO Obsidian Block ID" list should be reviewed even when it's non-empty and the run looks otherwise fine -- each one is a real content segment that had silently been missing an id; tell the user about any it finds, since it means their file had a gap they may not know about.

### How to run the whole pipeline

1. Stage the target file (and its outline file, for Task 1) via `device_stage_files` if it lives on the user's Obsidian vault.
2. **Re-stage right before each task**, not just once at the start of the conversation -- this file family is often edited live by the user in Obsidian while you're working on it in the same session. Diff the freshly staged copy against what you last worked from before assuming nothing changed; if it has, redo your analysis on the current content rather than risk clobbering the user's edits with stale output.
3. Run Task 1 (`align_headings.py`), review its summary. If Task 2 is being run in `--apply` mode (actually segmenting, not just checking), run it **next**, before Task 3 -- it changes block boundaries, so headings must already be correct (from Task 1) but body Block IDs must not be stamped yet (Task 3b runs after, to tag the new pieces). Then run Task 3a (`tag_heading_block_ids.py`) followed by 3b (`tag_body_block_ids.py`), in that order. Task 2 in **report mode** is the exception -- it can run independently at any point after Task 1 and never needs to run before delivering a file, since it only reads.
4. Each script writes its own timestamped backup next to the target before overwriting in place -- running the full pipeline leaves multiple backups, which is expected, not a bug.
5. Commit the final file back to its **original path** with `device_commit_files` (don't create a `_tagged`/`_numbered`/`_segmented` sibling file), using the `expectedMtimeMs` from your most recent stage of that exact file so a newer edit from the user is never silently overwritten.
6. Tell the user: how many headings were retagged (and flag any low-confidence matches you didn't already resolve); if Task 2 ran in `--apply` mode, how many segments were split and into how many pieces, and confirm Task 3b was re-run afterward; if Task 2 ran in report mode, how many long-segment candidates were found and where the report was sent; and the final Block ID ranges for both headings and body text.

### Notes on this file family

- These files are large (multi-thousand-line) Tibetan commentary text with embedded verse quotes (`>` blockquote lines), transclusion embeds (`![[other-file#^id]]`), and pre-existing partial Obsidian Block IDs mixed in with the heading structure. None of the scripts here ever touch verse-quote content or cross-file embeds beyond deciding whether to skip them.
- If a file in this set doesn't come with a companion ས་བཅད outline file, or uses a different chapter-heading convention than this skill assumes, ask the user rather than guessing -- these scripts are intentionally narrow to the conventions validated on this vault's files. Don't assume a missing outline means the whole skill is blocked: Task 2 and Task 3 don't need one (e.g. `BCAC16_PK_bo_segmented.md` had no outline anywhere in the vault and zero existing headings -- confirmed by filename/content search before asking -- so Task 1 was skipped on the user's confirmation and Tasks 2+3 ran alone; with no level-2 headings to key off of, every body segment ends up under a single label `"0"` in 3b, which is correct and expected until Task 1 can eventually run once an outline exists).
- **Segmenting a raw or freshly-received commentary from scratch** (no existing block structure at all, e.g. one giant paragraph per chapter): Task 2 `--apply` is the tool for this -- see "Apply mode" above. It only needs paragraph-level text to work on; it does not require Task 1/3 to have already run, though Task 1 should still run first if the file also needs heading alignment, since Task 2 skips heading lines when deciding what counts as a prose block. Always run Task 2 `--apply` before Task 3b so the newly-created pieces get proper Block IDs rather than being left anchor-less.
- This skill is distinct from **BCA-Heading-Level-Tagger** (also in this Skills folder), which targets an older convention where the ss-bcad numbering is typed bare directly into the commentary text (no separate outline file) and body Block IDs restart at every chapter rather than every level-2 heading. If it's unclear which convention a given file uses, ask the user before picking one.
