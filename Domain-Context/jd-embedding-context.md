# JD Embedding Pipeline — Domain Context

## Data Shape

`qualifications` and `responsibilities` are stored as JSON-encoded string arrays in SQLite:
- `NULL` — LLM extraction has not run yet for this job
- `"[]"` — LLM extraction ran but found no content in that section
- `'["3+ years Python", "BS CS required"]'` — normal populated value

Either field can be NULL or empty independently. A job description may legitimately have only responsibilities (e.g. early-career postings) or only qualifications (e.g. sparse listings). This is expected output from the LLM extraction step, not a data error.

## Embeddability Rule

A job is embeddable if **at least one** of `qualifications` or `responsibilities` is non-NULL and non-empty after JSON parsing. Both being empty (`[]`) indicates a failed LLM extraction — skip with a warning, do not embed.

## Embedding Text Format

Sections are labeled and joined with a blank line between them. Only include sections with content:

```
Responsibilities:
<bullet 1>
<bullet 2>

Qualifications:
<bullet 1>
<bullet 2>
```

If only one section exists, the text contains only that section with no trailing blank line.

## Storage Format

`jd_embedding` is a `BLOB` column storing raw IEEE 754 float32 bytes:
- Model: `voyage-3.5-lite` via Voyage AI
- Dimensions: 1024
- Size: 4 KB per vector (1024 × 4 bytes)
- Serialization: `np.array(vec, dtype=np.float32).tobytes()`
- Deserialization: `np.frombuffer(blob, dtype=np.float32)` → shape `(1024,)`

## Downstream Use

The stored vectors are intended for cosine similarity search against resume embeddings using an HNSW index. The float32 dtype and 1024-dim shape must be preserved consistently between the write path (this pipeline) and the read path (matching service).
