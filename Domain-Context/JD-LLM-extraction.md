# JD Extraction: Qualifications & Responsibilities

**Method:** Few-Shot Prompting + Implicit Prompt Caching  
**Model:** DeepSeek V3 0324 via OpenRouter  
**Task:** Extract structured qualifications and responsibilities from cleaned job descriptions

---

## What It Does

Each job description is sent to the LLM with a static system prompt containing:

- Extraction instructions
- 3 gold-labeled examples (few-shot)

The model returns a structured JSON object with two fields: `qualifications` and `responsibilities`.

The system prompt is identical across all calls, so OpenRouter's implicit caching kicks in automatically — the static prefix is computed once and reused, reducing effective input token cost on subsequent calls.

---

## Why We Chose This

| Reason                      | Detail                                                                                    |
| --------------------------- | ----------------------------------------------------------------------------------------- |
| **Easy to implement**       | No training data pipeline, no fine-tuning, no infrastructure — just an API call per row   |
| **Low cost at this scale**  | ~$0.06–0.12 for 584 rows; even at 10k rows cost stays under $2                            |
| **High precision & recall** | LLMs generalize well across varied JD formats where regex and rule-based approaches break |
| **Caching is free**         | DeepSeek implicit caching on OpenRouter requires zero config changes                      |

---

## Constraints This Fits

- Dataset is small — batch inference costs are negligible
- Job descriptions are pre-cleaned (`description_clean`) — no upstream noise to handle
- Output schema is simple (two flat lists) — low risk of hallucination or schema drift
- No latency requirement — offline batch processing, not real-time

---

## Trade-offs

**vs. Regex / Rule-based**  
Regex is free and fast but breaks on format variation. JDs are written in dozens of styles — no single pattern covers them. LLM handles this naturally.

**vs. Fine-tuned model**  
Fine-tuning gives the tightest precision/recall but requires labeled training data, a training run, and retraining when the schema changes. Overkill at this scale.

**vs. Larger models (GPT-4o, Claude Sonnet)**  
Would improve output quality marginally but cost 10–50x more per token with no meaningful gain on a structured extraction task this simple.

---

## Failure Modes

| Failure                                                | Likelihood | Mitigation                                                                    |
| ------------------------------------------------------ | ---------- | ----------------------------------------------------------------------------- |
| Model conflates qualifications and responsibilities    | Low–Medium | Few-shot examples explicitly separate them; add a validation step             |
| Sparse output on short/malformed JDs                   | Low        | Skip rows where both `qualifications` and `responsibilities` are empty; at least one must be non-empty |
| Cache miss on every call                               | Low        | OpenRouter sticky routing handles this; verify with `usage` field in response |
| Schema drift (model returns free text instead of JSON) | Low        | Use `response_format: { type: "json_object" }` in the API call                |
| Few-shot examples bias output format                   | Medium     | Use diverse examples that cover multiple JD writing styles                    |

---

## Token & Cost Summary

|                                     | Tokens per call |
| ----------------------------------- | --------------- |
| System prompt + 3 examples (cached) | ~1,700          |
| Job description (variable)          | ~1,297 avg      |
| Output (quals + responsibilities)   | ~410            |

| Scenario                             | 300 rows | 584 rows |
| ------------------------------------ | -------- | -------- |
| No caching                           | $0.062   | $0.121   |
| 50% cache discount (conservative)    | $0.047   | $0.091   |
| 90% cache discount (DeepSeek native) | $0.035   | $0.068   |

Caching savings are modest at this scale. The architecture pays off above ~10k rows.

---

## Implementation Notes

- **Seed your sample** with `random_state=42` for reproducibility (`jobs_sample_300.csv`)
- **Cache is implicit** — no `cache_control` headers needed; just keep the system prompt identical across calls
- **Validate outputs** — check that both fields are non-empty lists before writing to disk
- **Scale path** — this method runs unchanged at 10k+ rows; cost stays linear and caching savings grow
