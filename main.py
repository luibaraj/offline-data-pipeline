#!/usr/bin/env python3
import argparse
import logging
import config
import scraper.scraper as scraper
import storage.db as db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def cmd_scrape(args):
    db.init()
    jobs = scraper.scrape_paginated(args.term, args.location, args.results)
    saved = db.save_jobs(jobs)
    logger.info("Done: %d new jobs saved (of %d scraped)", saved, len(jobs))


def cmd_search(args):
    rows = db.search_jobs(keyword=args.keyword, limit=args.limit)
    for row in rows:
        print(f"{row['date_posted']}  {row['company']:<30}  {row['title']:<50}  {row['job_url']}")


def main():
    parser = argparse.ArgumentParser(description="LinkedIn job scraper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scrape = sub.add_parser("scrape", help="Scrape jobs and store them")
    p_scrape.add_argument("term", help="Search term, e.g. 'machine learning engineer'")
    p_scrape.add_argument("location", help="Location, e.g. 'San Francisco, CA'")
    p_scrape.add_argument("--results", type=int, default=config.RESULTS_PER_SEARCH, help="Results per search term")
    p_scrape.set_defaults(func=cmd_scrape)

    p_search = sub.add_parser("search", help="Search stored jobs")
    p_search.add_argument("keyword", nargs="?", default="", help="Keyword to filter by title/description")
    p_search.add_argument("--limit", type=int, default=50)
    p_search.set_defaults(func=cmd_search)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
