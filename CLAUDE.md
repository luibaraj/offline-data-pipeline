# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Coding Principles

**Philosophy: Do the simplest thing that works.**

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

This is a personal LinkedIn job scraping project using the [JobSpy](https://github.com/Bunsly/JobSpy) open-source library. The goal is to scrape LinkedIn job listings for personal job search purposes at low scale (~300 jobs/day).

**Key Legal & Risk Context:**

- Uses JobSpy's guest endpoints (no authentication required) — your personal account cannot be banned
- Scraping public data is legally protected per the hiQ Labs v. LinkedIn (9th Circuit, 2022) ruling
- IP blocking risk is mitigated using rotating residential proxies (Webshare)

Refer to `Domain-Context/linkedin-scraping-strategy.md` for the full risk analysis and operational guidelines.

## Architecture Expectations

When implementing the scraper, follow these patterns:

### Request Obfuscation (Required)

- **Jitter:** Add random delays between requests (2.5–8 seconds, not fixed intervals)
- **User-Agent Rotation:** Randomize the `User-Agent` header per request (5–10 variations minimum)
- **Proxies:** Route all scraping through Webshare rotating residential proxies to isolate your home IP

### Key Constraints

- Scale is intentionally low: ~300 jobs/day to remain undetectable
- Never create fake LinkedIn accounts (this is where legal risk increases)
- Do not modify or bypass authentication mechanisms
- JobSpy handles the actual scraping via guest endpoints — use its API as documented

### Expected Modules

When building out the scraper, expect to organize code into:

- A scraper module that wraps JobSpy with obfuscation (jitter, user-agent rotation, proxy handling)
- A storage/database layer for persisting scraped job data
- A filtering/search layer for finding relevant jobs
- CLI or configuration layer for specifying search terms, locations, volume

## Development Commands

(To be populated once the project structure is created)

## Testing

(To be populated once tests are added)

## Deployment & Operational Notes

- **Webshare Proxies:** Store credentials securely in environment variables (never commit)
- **Job Data Storage:** Plan for efficient querying and deduplication of jobs across runs
- **Monitoring:** Log scraping activity to detect if IP blocks or rate limiting occurs
- **Graceful Degradation:** Handle proxy IP blocks by rotating to fresh proxies without losing state
