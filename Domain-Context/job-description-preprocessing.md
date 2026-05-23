# Job Description Preprocessing

## Context

**Source:** LinkedIn job listings scraped via automated scraper  
**Use case:** Semantic search and job-resume matching using embedding models and cross-encoders

---

## What the data actually is

LinkedIn's scraper does not return raw HTML. It returns a **markdown-like intermediate format** — HTML has already been partially converted before export. This means HTML-specific cleaning (tag stripping, entity unescaping) is unnecessary. The noise that actually exists is markdown formatting artifacts, structural whitespace, and content-level issues described below.

---

## Preprocessing Steps

### 1. Unescape Markdown Backslash Escapes

LinkedIn encodes special characters with a preceding backslash (e.g., `\-`, `\&`, `\#`, `\*`). These are formatting artifacts from their internal HTML-to-markdown conversion — not meaningful content.

**Why it matters:** Without this step, a hyphenated term like `machine\-learning` is not the same string as `machine-learning`. Tokenizers may split them differently, producing inconsistent token sequences and subtly different embeddings for identical concepts.

---

### 2. Strip Markdown Bold and Italic Formatting

Job descriptions use `**bold**` and `*italic*` markers extensively — almost exclusively for section headers and labels (e.g., `**About the Role**`, `**Requirements**`). The formatting carries no semantic content; only the words matter.

**Why it matters:** Asterisk tokens are noise. The word "Requirements" and the string `**Requirements**` should produce the same embedding. Orphaned or unclosed markers (e.g., a stray `**` at end of line) are also stripped in a second pass.

**Known limitation:** Section headers like `**About the Role**` become plain text labels like `About the Role` — they are not removed. This is intentional; the words themselves may carry weak but real signal.

---

### 3. Replace Non-Breaking Spaces

Sixteen rows contain `\xa0` (the non-breaking space character, equivalent to HTML `&nbsp;`). These are invisible — they look identical to regular spaces in any editor or display.

**Why it matters:** Tokenizers treat `\xa0` as a distinct character from a regular space. `"machine\xa0learning"` and `"machine learning"` may tokenize differently, producing inconsistent embeddings for what is visually the same text.

**Fix:** Simple character replacement — replace all `\xa0` with a standard space before any other processing.

---

### 4. Unicode Normalization (NFKC)

Descriptions contain typographic characters that have ASCII equivalents: smart/curly quotes (`"` `"` `'` `'`), em-dashes (`—`), and non-standard bullet characters (`•`, `·`). These appear in 12, 46, and 8 rows respectively.

**Why it matters:** The same word surrounded by different quote styles produces different token sequences. NFKC normalization is the standard unicode compatibility normalization — it converts these to their ASCII equivalents while preserving all actual content.

**Note:** This step runs after `\xa0` replacement because NFKC does not always normalize non-breaking spaces reliably across all tokenizers.

---

### 5. Whitespace Normalization

Raw descriptions contain heavy structural whitespace inherited from LinkedIn's HTML layout: sequences of `\n   \n\n  \n` where a visual section break existed in the original page. Multiple consecutive blank lines and irregular spacing throughout.

**Why it matters:** Excess whitespace wastes context window and adds padding tokens. Three blank lines and one blank line are semantically identical — both mean "section break." This step collapses runs of 3+ newlines to 2, and multiple spaces/tabs to one.

---

### 6. Deduplication

25 rows (13%) are exact duplicates — same company, same job title, same description content — posted under different LinkedIn job IDs and URLs. The most extreme case is a single Mindrift role appearing 15 times with unique IDs.

**Why it matters:** Duplicate descriptions inflate the apparent weight of those roles in any downstream process. In retrieval, returning the same job 15 times is a poor user experience. In any fine-tuning or training scenario, duplicates receive proportionally more gradient updates.

**Deduplication key:** `(company, title, cleaned_description)`. Deduplicating on ID or URL alone would miss these, as each posting has a unique identifier. Deduplicating on `(company, title)` alone would incorrectly collapse genuinely different postings for the same role in different locations.

**Result:** 186 → 161 rows.

---

## Explicitly Out of Scope

The following were investigated and ruled out as non-issues for this use case:

- **HTML tag stripping / entity unescaping:** Not present in the data. LinkedIn pre-processes before export.
- **Token length / chunking:** Embedding and reranker models in use have sufficient context windows for the description lengths observed.
- **Metadata extraction (salary, remote/hybrid, visa, clearance):** Metadata is present in descriptions but not extracted as structured fields. This is acceptable for the current use case.
- **Recruiter/aggregator boilerplate** (Jobright, Haystack openers): Present in ~4 rows. Not worth the complexity.
- **`date_posted` nulls:** 178/186 rows are null. The `scraped_at` field is used as a recency proxy instead.

---

## Known Unresolved Issues

- **Metadata leakage in embeddings:** Salary figures, location labels, and visa language remain in description text after cleaning. For pure semantic similarity this is low-risk. If embeddings are ever used as features in a supervised model, this should be revisited — a resume mentioning "San Francisco" or a salary expectation could match jobs on geographic/compensation text rather than role content.

- **Structured label artifacts:** Bold section labels (e.g., `**Location:** Atlanta, GA`) become plain text after Step 2: `Location: Atlanta, GA`. This content is not stripped. These labels are minor noise but could in theory skew similarity for queries containing those words.

- **EEO boilerplate not stripped:** 69 rows (37%) contain standard Equal Employment Opportunity legal text, nearly identical across companies. This creates a false similarity floor — roles that share nothing in common are pulled closer in embedding space because they share 150–300 words of identical legal text. Not currently stripped because EEO text occasionally appears mid-description (17/69 cases), making a clean terminal strip unreliable without manual review.

- **Embedded URLs not stripped:** 20 rows contain raw URLs inside the description text, typically links to application portals or benefit documents. These are long, structurally noisy token sequences with no semantic signal for role matching. Deferred pending a decision on whether any URLs carry useful signal (e.g., company domain as a weak company-identity cue).

- **Scraper consistency:** The data format (markdown-like) reflects LinkedIn's current output format. If the scraper source or LinkedIn's export format changes, steps 1–2 may become incorrect and steps that were skipped (HTML entity unescaping, tag stripping) may become necessary. The preprocessing assumptions should be re-validated on any new data batch.
