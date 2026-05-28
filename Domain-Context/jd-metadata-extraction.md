# JD Metadata Extraction (`extract-meta` step)

After LLM extraction of `qualifications` and `responsibilities`, a second step parses structured metadata from those fields. This step runs entirely offline and produces three columns.

---

## Fields Produced

| Column | Type | Method | Description |
| --- | --- | --- | --- |
| `max_yoe` | `INTEGER \| NULL` | LLM | Years of experience required, parsed from qualifications bullets |
| `min_education` | `TEXT \| NULL` | LLM | Lowest degree tier mentioned: `"BS"`, `"MS"`, or `"PhD"` |
| `is_internship` | `INTEGER` | Regex | `1` if the job title matches internship patterns, `0` otherwise |

---

## `max_yoe` and `min_education` — LLM Extraction

These are extracted by a second LLM call (`_qual_meta_chain` in `storage/extract.py`) that receives the structured `qualifications` list and returns a typed JSON object.

**Why LLM here too:** Years of experience and education requirements appear in highly varied phrasing across JDs ("5+ years", "at least five years", "two to four years of experience"). Regex brittle; LLM handles the variation naturally.

**Extraction rules applied by the model:**

- `max_yoe`: If any bullet uses `x+` format, return the highest `x`. If only bounded ranges exist, return the lower bound. Null if no years stated.
- `min_education`: Map to the lowest tier mentioned (`BS` < `MS` < `PhD`). Null if no degree required.

**Senior-title fallback:** If `max_yoe` is null after LLM extraction but the job title matches `senior|sr|staff|lead|founder`, `max_yoe` defaults to `5`. This handles postings that imply seniority without stating years explicitly.

---

## `is_internship` — Regex on Title

Set by matching the job **title only** against a fixed pattern. Description text is not consulted.

**Regex:** `\b(intern(ship)?|co[\s-]?op)\b` (case-insensitive)

| Pattern | Example match |
| --- | --- |
| `intern` | "Software Intern", "ML Intern 2025" |
| `internship` | "Software Engineering Internship" |
| `co-op` | "Data Science Co-op" |
| `co op` | "Co Op Engineer" |
| `coop` | "Coop Position" |

Word boundaries prevent false matches on `internal`, `coordinator`, etc.

**Why regex instead of LLM:** The signal is categorical and unambiguous. Job titles use a small, stable vocabulary for internship roles. Regex is free, instant, and has no failure modes here — LLM would add latency and cost with no accuracy gain.

**Why title only:** Titles are the authoritative signal for role type. Description text is noisier — it may mention internship programs, past interns, or intern-facing teams without the role itself being an internship.

**Downstream use:** `is_internship` is stored and kept in the ChromaDB index. Filtering is applied at query time by the matching layer, not at indexing time.

---

## Back-fill Behavior

`get_jobs_missing_qual_meta()` gates on `(max_yoe IS NULL OR is_internship IS NULL)`. This means running `extract-meta` after adding a new metadata field will automatically back-fill that field for all rows that already have `qualifications` populated — no separate migration command needed.
