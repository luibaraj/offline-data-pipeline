#!/usr/bin/env python3
import argparse
import logging
import config
import scraper.scraper as scraper
import storage.db as db
from storage.preprocess import clean_description

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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
