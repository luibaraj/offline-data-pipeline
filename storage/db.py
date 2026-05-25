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
        existing = {row[1] for row in con.execute("PRAGMA table_info(jobs)")}
        if "description_clean" not in existing:
            con.execute("ALTER TABLE jobs ADD COLUMN description_clean TEXT")
        if "qualifications" not in existing:
            con.execute("ALTER TABLE jobs ADD COLUMN qualifications TEXT")
        if "responsibilities" not in existing:
            con.execute("ALTER TABLE jobs ADD COLUMN responsibilities TEXT")
        if "max_yoe" not in existing:
            con.execute("ALTER TABLE jobs ADD COLUMN max_yoe INTEGER")
        if "min_education" not in existing:
            con.execute("ALTER TABLE jobs ADD COLUMN min_education TEXT")


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


def get_unextracted_jobs() -> list[sqlite3.Row]:
    with _conn() as con:
        return con.execute(
            "SELECT id, description_clean FROM jobs WHERE description_clean IS NOT NULL AND qualifications IS NULL"
        ).fetchall()


def update_extracted_fields(job_id: str, qualifications: list[str], responsibilities: list[str]):
    import json
    with _conn() as con:
        con.execute(
            "UPDATE jobs SET qualifications = ?, responsibilities = ? WHERE id = ?",
            (json.dumps(qualifications), json.dumps(responsibilities), job_id),
        )


def get_jobs_missing_qual_meta() -> list[sqlite3.Row]:
    with _conn() as con:
        return con.execute(
            "SELECT id, qualifications FROM jobs WHERE qualifications IS NOT NULL AND max_yoe IS NULL"
        ).fetchall()


def update_qual_meta(job_id: str, max_yoe: int | None, min_education: str | None):
    with _conn() as con:
        con.execute(
            "UPDATE jobs SET max_yoe=?, min_education=? WHERE id=?",
            (max_yoe, min_education, job_id),
        )


def search_jobs(keyword: str = "", limit: int = 50, hours: int | None = None) -> list[sqlite3.Row]:
    with _conn() as con:
        conditions = []
        params: list = []
        if keyword:
            conditions.append("(title LIKE ? OR COALESCE(description_clean, description) LIKE ?)")
            pattern = f"%{keyword}%"
            params.extend([pattern, pattern])
        if hours is not None:
            conditions.append("scraped_at >= datetime('now', ? || ' hours')")
            params.append(f"-{hours}")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        return con.execute(
            f"SELECT * FROM jobs {where} ORDER BY scraped_at DESC LIMIT ?", params
        ).fetchall()
