import time
import random
import logging
from jobspy import scrape_jobs
import config

logger = logging.getLogger(__name__)


def _scrape_batch(search_term: str, location: str, offset: int) -> list[dict]:
    user_agent = random.choice(config.USER_AGENTS)
    proxies = [config.PROXY_URL] if config.PROXY_URL else None

    df = scrape_jobs(
        site_name=["linkedin"],
        search_term=search_term,
        location=location,
        results_wanted=config.RESULTS_PER_SEARCH,
        offset=offset,
        hours_old=24,
        proxies=proxies,
        headers={"User-Agent": user_agent},
    )
    return df.to_dict("records")


def scrape_paginated(search_term: str, location: str, total: int) -> list[dict]:
    all_jobs = []
    offset = 0
    logger.info("Scraping: '%s' in '%s' (%d total)", search_term, location, total)

    while offset < total:
        batch = _scrape_batch(search_term, location, offset)
        all_jobs.extend(batch)
        logger.info("Fetched %d jobs (offset=%d, total so far=%d)", len(batch), offset, len(all_jobs))

        offset += config.RESULTS_PER_SEARCH
        if offset < total and batch:
            delay = random.uniform(config.JITTER_MIN, config.JITTER_MAX)
            logger.debug("Jitter: sleeping %.1fs", delay)
            time.sleep(delay)

        if len(batch) < config.RESULTS_PER_SEARCH:
            logger.info("LinkedIn returned fewer results than requested — stopping early")
            break

    return all_jobs
