#!/usr/bin/env python3
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import config
import scraper.scraper as scraper
import storage.db as db
from storage.preprocess import clean_description
from storage.extract import extract_jd_fields

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def cmd_scrape(args):
    db.init()
    all_jobs = []
    for term in config.SEARCH_TERMS:
        all_jobs.extend(scraper.scrape_paginated(term, args.location, config.RESULTS_PER_TERM))
    saved = db.save_jobs(all_jobs)
    logger.info("Done: %d new jobs saved (of %d scraped)", saved, len(all_jobs))


def cmd_preprocess(args):
    db.init()
    with db._conn() as con:
        rows = con.execute(
            "SELECT id, description FROM jobs WHERE description_clean IS NULL AND description IS NOT NULL"
        ).fetchall()
        for row in rows:
            con.execute(
                "UPDATE jobs SET description_clean = ? WHERE id = ?",
                (clean_description(row["description"]), row["id"]),
            )
    logger.info("Preprocessed %d job descriptions", len(rows))


def cmd_extract(args):
    db.init()
    rows = db.get_unextracted_jobs()
    logger.info("Extracting fields for %d jobs", len(rows))

    results = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(extract_jd_fields, row["description_clean"]): row["id"] for row in rows}
        for future in as_completed(futures):
            job_id = futures[future]
            try:
                result = future.result()
                if not result.qualifications and not result.responsibilities:
                    logger.warning("No qualifications or responsibilities extracted for job %s — skipping", job_id)
                else:
                    results[job_id] = result
            except Exception as e:
                logger.warning("Extraction failed for job %s: %s", job_id, e)

    saved = 0
    for job_id, result in results.items():
        db.update_extracted_fields(job_id, result.qualifications, result.responsibilities)
        saved += 1

    logger.info("Done: %d/%d jobs extracted", saved, len(rows))


def cmd_search(args):
    rows = db.search_jobs(keyword=args.keyword, limit=args.limit, hours=args.since)
    for row in rows:
        print(f"{row['date_posted']}  {row['company']:<30}  {row['title']:<50}  {row['job_url']}")


def main():
    parser = argparse.ArgumentParser(description="LinkedIn job scraper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scrape = sub.add_parser("scrape", help="Scrape jobs and store them")
    p_scrape.add_argument("--location", default="United States", help="Location, e.g. 'San Francisco, CA'")
    p_scrape.set_defaults(func=cmd_scrape)

    p_search = sub.add_parser("search", help="Search stored jobs")
    p_search.add_argument("keyword", nargs="?", default="", help="Keyword to filter by title/description")
    p_search.add_argument("--limit", type=int, default=50)
    p_search.add_argument("--since", type=int, default=None, metavar="HOURS", help="Only jobs scraped within the last N hours")
    p_search.set_defaults(func=cmd_search)

    sub.add_parser("preprocess", help="Clean stored descriptions into description_clean").set_defaults(func=cmd_preprocess)
    sub.add_parser("extract", help="Extract qualifications and responsibilities via LLM").set_defaults(func=cmd_extract)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
