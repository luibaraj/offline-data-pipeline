import sqlite3
import logging
from contextlib import contextmanager
import config

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id          TEXT PRIMARY KEY,
    title       TEXT,
    company     TEXT,
    location    TEXT,
    job_url     TEXT UNIQUE,
    description TEXT,
    date_posted TEXT,
    scraped_at  TEXT DEFAULT (datetime('now'))
)
"""


@contextmanager
def _conn():
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init():
    with _conn() as con:
        con.execute(SCHEMA)


def save_jobs(jobs: list[dict]) -> int:
    inserted = 0
    with _conn() as con:
        for job in jobs:
            try:
                con.execute(
                    """INSERT OR IGNORE INTO jobs (id, title, company, location, job_url, description, date_posted)
                       VALUES (:id, :title, :company, :location, :job_url, :description, :date_posted)""",
                    {
                        "id": job.get("id") or job.get("job_url"),
                        "title": job.get("title"),
                        "company": job.get("company"),
                        "location": job.get("location"),
                        "job_url": job.get("job_url"),
                        "description": job.get("description"),
                        "date_posted": str(job.get("date_posted", "")),
                    },
                )
                inserted += con.execute("SELECT changes()").fetchone()[0]
            except Exception as e:
                logger.error("Failed to save job %s: %s", job.get("job_url"), e)
    return inserted


def search_jobs(keyword: str = "", limit: int = 50) -> list[sqlite3.Row]:
    with _conn() as con:
        if keyword:
            pattern = f"%{keyword}%"
            return con.execute(
                "SELECT * FROM jobs WHERE title LIKE ? OR description LIKE ? ORDER BY scraped_at DESC LIMIT ?",
                (pattern, pattern, limit),
            ).fetchall()
        return con.execute(
            "SELECT * FROM jobs ORDER BY scraped_at DESC LIMIT ?", (limit,)
        ).fetchall()
