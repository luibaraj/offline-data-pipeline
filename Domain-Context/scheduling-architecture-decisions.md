# Scheduling & Architecture Decisions

## Scheduling Strategy

**Chosen: GitHub Actions cron (free tier)**

- 2,000 free minutes/month; 4 runs/day × ~1 min = ~120 min/month — well within limits
- Runs on GitHub's infrastructure — Mac does not need to be on or awake
- All scraping traffic still routes through Webshare residential proxies; LinkedIn sees residential IPs, not GitHub datacenter IPs
- Schedule: every 6 hours (4×/day), 2 terms × 38 results/term ≈ 75 jobs/run = ~300 jobs/day

**Rejected alternatives:**

| Option                            | Reason rejected                                               |
| --------------------------------- | ------------------------------------------------------------- |
| macOS `launchd` / `cron`          | Requires Mac to be on and awake                               |
| Python `schedule` loop            | Requires persistent running process                           |
| Free-tier cloud VM (Oracle, etc.) | More ops overhead; datacenter IP hits proxy chain differently |

---

## Data Persistence

**Problem:** GitHub Actions runners are ephemeral — `jobs.db` is destroyed after each run.

**Solution:** Commit `jobs.db` back to a private GitHub repo after each run using `git push`.

- Simple, free, no external dependencies
- Private repo ensures job data is not publicly exposed
- `INSERT OR IGNORE` on `id` (PRIMARY KEY) and `job_url` (UNIQUE) already handles deduplication across runs — same job appearing in multiple batches is silently ignored

**Trade-off accepted:** SQLite in a git repo is not ideal for large datasets or concurrent access, but at ~300 jobs/day it is sufficient indefinitely.

---

## Known Constraints & Risks

### Detection

- **TLS/HTTP fingerprinting gap:** User-Agent rotation does not change JobSpy's underlying HTTP/TLS fingerprint. Mitigated in practice by rotating residential proxies — no single IP accumulates enough requests for LinkedIn to pattern-match on the fingerprint at ~300 jobs/day. Residual risk is negligible at this scale.
- **Burst behavior:** ~75 jobs in minutes is more detectable than spread across the day. The 6-hour schedule with random startup jitter (0–20 min) directly mitigates this.
- **Proxy rotation opacity:** Webshare controls how frequently IPs rotate — you don't control this. If a proxy IP is flagged, Webshare rotates automatically, but there is a gap window. Mitigated in practice by per-connection rotation — each request already uses a fresh IP, so no single IP accumulates requests during a gap. Residual risk is only if Webshare's rotation fails or reuses an IP, which is outside your control.
- **Guest endpoint monitoring:** LinkedIn may monitor unauthenticated endpoints more aggressively than authenticated ones — unknown.

### Legal

- **hiQ Labs v. LinkedIn (9th Circuit, 2022)** is a _preliminary injunction_, not a final merits ruling. It settled without Supreme Court review.
- hiQ protects against **CFAA claims** only. LinkedIn's **ToS violation claims under state contract law** are a separate legal theory not addressed by hiQ.
- Protection is anchored to **personal, non-commercial use**. Commercializing or publishing the scraped data materially changes the legal calculus.
- hiQ precedent is 9th Circuit only (though no other circuit has ruled against it).

### Operational

- **JobSpy maintenance risk:** JobSpy scrapes undocumented LinkedIn guest endpoints. LinkedIn can change these without notice, causing silent empty results. Monitor the `saved=0` log line as a health signal.
- **Result quality degradation:** LinkedIn relevance ranking degrades past ~100 results per query. Current setup uses 38 results per term — well within the reliable relevance range.

---

## Operational Guidelines (updated)

- Run 4×/day, every 6 hours; apply a random startup delay (0–20 minutes) to jitter the fixed interval
- 2 search terms × 38 results/term ≈ 75 jobs/run; page size is 25 results/batch
- `hours_old=6` is set in the scraper — fetches only jobs posted since the last run
- Never commit `WEBSHARE_PROXY_URL` or any credentials — store in GitHub Actions secrets
- Monitor for `saved=0` across consecutive runs as a signal that JobSpy's endpoints have broken
