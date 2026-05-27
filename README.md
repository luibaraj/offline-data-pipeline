# Offline Data Pipeline — Resume-Job Matching Engine

Builds and maintains a structured, semantically-indexed job corpus for downstream resume-job matching. It scrapes LinkedIn job listings, cleans and normalizes descriptions, extracts structured fields via LLM, generates vector embeddings, and writes a searchable index — all on a recurring schedule via GitHub Actions. The resulting SQLite database and ChromaDB index are consumed by the online matching pipeline (retrieval → rerank → generate recommendations).

## Pipeline

```
scrape → preprocess → extract → extract-meta → embed → index
```

| Stage            | Command                                                | What it does                                                                                             |
| ---------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| **scrape**       | `python main.py scrape --location "San Francisco, CA"` | Fetches ~300 jobs/day via [JobSpy](https://github.com/Bunsly/JobSpy) and saves to `jobs.db`              |
| **preprocess**   | `python main.py preprocess`                            | Cleans raw descriptions (unicode normalization, markdown stripping, whitespace) into `description_clean` |
| **extract**      | `python main.py extract`                               | Uses DeepSeek V3 via OpenRouter to pull `qualifications` and `responsibilities` arrays from each JD      |
| **extract-meta** | `python main.py extract-meta`                          | Parses min education (BS/MS/PhD) and max years of experience from qualifications                         |
| **embed**        | `python main.py embed`                                 | Generates 1024-dim embeddings via Voyage AI `voyage-3.5-lite` and stores as binary blobs                 |
| **index**        | `python main.py index`                                 | Upserts embeddings + metadata into a ChromaDB HNSW index for cosine similarity search                    |

## Setup

```bash
git clone <repo>
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
WEBSHARE_PROXY_URL=http://user:pass@proxy.webshare.io:port
OPENROUTER_API_KEY=sk-...
VOYAGE_API_KEY=pa-...
```

- **WEBSHARE_PROXY_URL** — rotating residential proxy for scraping ([Webshare](https://www.webshare.io/))
- **OPENROUTER_API_KEY** — used for LLM extraction
- **VOYAGE_API_KEY** — used for embedding generation

## Automated Scheduling

A GitHub Actions workflow (`.github/workflows/scrape.yml`) runs the full pipeline every 6 hours. After each run it commits `jobs.db` back to the repo. The workflow uses a random 0–20 minute startup jitter to avoid predictable timing patterns.

Set the following secrets at **Settings → Secrets and variables → Actions** in your GitHub repo — never commit them:

| Secret               | Purpose                                             |
| -------------------- | --------------------------------------------------- |
| `WEBSHARE_PROXY_URL` | Rotating residential proxy credentials for scraping |
| `OPENROUTER_API_KEY` | LLM extraction via DeepSeek V3                      |
| `VOYAGE_API_KEY`     | Embedding generation via Voyage AI                  |

## Output & Downstream Use

This pipeline produces two artifacts consumed by the online matching pipeline:

- **`jobs.db`** — SQLite database with cleaned descriptions, extracted qualifications/responsibilities, and structured metadata (YOE, education level)
- **`chroma_index/`** — ChromaDB HNSW index of 1024-dim job embeddings with cosine similarity, queryable by the online pipeline for candidate retrieval

Retrieval, reranking, and recommendation generation are handled separately in the online pipeline.

## Legal & Risk

- Scrapes **public LinkedIn data only** via guest endpoints — no authentication, no fake accounts
- Legal basis: [hiQ Labs v. LinkedIn](https://cdn.ca9.uscourts.gov/datastore/opinions/2022/04/18/17-16783.pdf) (9th Cir. 2022) protects scraping of publicly accessible data
- Detection mitigations: 2.5–8s random jitter between requests, 7 rotating User-Agent strings, Webshare residential proxies
- Scale is intentionally low (~300 jobs/day); personal, non-commercial use only
