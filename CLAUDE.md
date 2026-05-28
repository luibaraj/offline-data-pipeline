# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Coding Principles

**Philosophy 1: Do the simplest thing that works.**

**Philosophy 2: Make zero assumptions or decisions about system design and implementaiton at any level of the project. Ask the user for clarifiaciton and context.**

### Simplicity & Conciseness

- Write the minimum code needed to solve the problem correctly — no more
- Delete code that isn't doing meaningful work; dead code is a liability
- Prefer a clear 10-line function over an abstracted 50-line one
- No speculative abstractions: don't build for hypothetical future requirements
- Create/Edit the least number of files necessary for each task

### Logging

Log only where execution is hard to trace: proxy failures, unexpected branches, and operation outcomes. Avoid logging in straightforward code paths.

- `DEBUG` — tricky request-level details
- `INFO` — top-level operation start/finish
- `WARNING` — recoverable failures (retries, rotations)
- `ERROR` — unrecoverable failures

### What to Avoid

- Commented-out code (delete it; git has history)
- Wrapper functions that only call one other function with no added logic
- Generic exception handling that silently swallows errors (`except Exception: pass`)

## Project Overview

Personal LinkedIn job scraping tool using [JobSpy](https://github.com/Bunsly/JobSpy). Scrapes LinkedIn job listings at low scale (~300 jobs/day) and stores them in a local SQLite database for search and export.

**Key Legal & Risk Context:**

- Uses JobSpy's guest endpoints (no authentication required) — your personal account cannot be banned
- Scraping public data is legally protected per the hiQ Labs v. LinkedIn (9th Circuit, 2022) ruling
- IP blocking risk is mitigated using rotating residential proxies (Webshare)

Refer to `Domain-Context/linkedin-scraping-strategy.md` for the full risk analysis and operational guidelines.

## Architecture

### Module Layout

- `config.py` — central config: `PROXY_URL`, `USER_AGENTS` (7 entries), `SEARCH_TERMS`, `JITTER_MIN/MAX`, `RESULTS_PER_SEARCH`, `RESULTS_PER_TERM`, `DB_PATH`
- `scraper/scraper.py` — JobSpy wrapper; `_check_proxy()` validates proxy at startup, `_scrape_batch()` makes a single paginated call, `scrape_paginated()` orchestrates multi-batch scraping with jitter delays between batches
- `storage/db.py` — SQLite layer; `init()` creates schema and runs additive migration adding `description_clean TEXT` column (safe to re-run on existing DBs), `save_jobs()` inserts with `INSERT OR IGNORE` (deduplication via `id` PRIMARY KEY + `job_url` UNIQUE), `search_jobs()` filters by keyword + recency, querying `COALESCE(description_clean, description)` to prefer cleaned text when populated
- `storage/preprocess.py` — `clean_description(text)` normalizes raw LinkedIn job descriptions: replaces `\xa0`, applies NFKC unicode normalization, unescapes LinkedIn markdown backslash sequences, strips bold/italic markers, and collapses whitespace. No external dependencies.
- `main.py` — CLI: `scrape` command runs all `SEARCH_TERMS` and saves to DB; `search` command queries DB and prints a table; `preprocess` command cleans all raw descriptions and populates `description_clean` (idempotent)
- `export.py` — dumps all DB rows to `jobs_export.csv`

### Request Obfuscation (Required)

All scraping must maintain these obfuscation techniques. Do not remove or bypass them:

- **Jitter:** Random delays between requests (`JITTER_MIN`–`JITTER_MAX` seconds, not fixed)
- **User-Agent Rotation:** Random `User-Agent` selected per request from `USER_AGENTS` in `config.py`
- **Proxies:** All requests routed through Webshare rotating residential proxies via `PROXY_URL`

### Key Constraints

- Scale is intentionally low: ~300 jobs/day to remain undetectable
- Never create fake LinkedIn accounts (this is where legal risk increases)
- Do not modify or bypass authentication mechanisms
- JobSpy handles the actual scraping via guest endpoints — use its API as documented

## Development Commands

```bash
# Scrape jobs for all SEARCH_TERMS defined in config.py
python main.py scrape --location "San Francisco, CA"

# Search the local DB by keyword (--since is hours)
python main.py search "machine learning" --limit 20 --since 24

# Clean raw job descriptions and write to description_clean column (idempotent)
python main.py preprocess

# Export all jobs to jobs_export.csv
python export.py
```

## Testing

No test suite. Manual verification: run `python main.py search` after a scrape run to confirm new jobs were saved. If adding tests, `storage/db.py` and the pagination logic in `scraper/scraper.py` are the highest-value targets.

## Deployment & Operational Notes

- **Scheduler:** GitHub Actions cron (`.github/workflows/scrape.yml`) — runs every 6 hours
- **Workflow sequence:** delete jobs older than 2 days → sleep 0–20 min (startup jitter) → scrape → commit `jobs.db` back to repo with `[skip ci]`
- **Proxy credential:** `WEBSHARE_PROXY_URL` is a GitHub Actions secret — set it there, never in code or committed files
- **Data persistence:** `jobs.db` is committed to the repo after every run (private repo — this is intentional)
- **Health check:** If `saved=0` consistently across runs, the guest endpoint or proxy rotation is likely failing — check Actions logs

## Data Pipeline (Future)

**Text Cleaning — Implemented:** `clean_description()` in `storage/preprocess.py` normalizes raw descriptions; `main.py preprocess` populates `description_clean` column. Known gaps: EEO boilerplate (~37% of rows), embedded URLs, metadata leakage in embeddings, structured label artifacts from bold headers.

**Remaining work** (documented in `Domain-Context/data-pipeline-checklist.md`):

- Metadata extraction: degree parsing, seniority binning, experience year extraction
- Dense embedding generation (1024-dim, batched at 128)
- HNSW vector index with cosine distance

See `Domain-Context/job-description-preprocessing.md` for technical rationale of each cleaning step.
