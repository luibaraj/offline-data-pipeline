import json
import sqlite3
import numpy as np
import pytest
import storage.db as db
from conftest import make_job


def _raw(con, sql, params=()):
    return con.execute(sql, params).fetchall()


def test_init_idempotent():
    db.init()  # called a second time (fixture already called once)
    with db._conn() as con:
        cols = [row[1] for row in con.execute("PRAGMA table_info(jobs)")]
    expected = [
        "id", "title", "company", "location", "job_url", "description",
        "date_posted", "scraped_at", "description_clean", "qualifications",
        "responsibilities", "max_yoe", "min_education", "jd_embedding", "description_hash",
    ]
    for col in expected:
        assert cols.count(col) == 1, f"column '{col}' appears {cols.count(col)} times"


def test_save_jobs_returns_inserted_count():
    jobs = [
        make_job(id="a", job_url="http://x/a", description="desc a"),
        make_job(id="b", job_url="http://x/b", description="desc b"),
    ]
    assert db.save_jobs(jobs) == 2


def test_save_jobs_dedup_same_id():
    job = make_job(id="dup", job_url="http://x/1")
    assert db.save_jobs([job, job]) == 1
    with db._conn() as con:
        assert len(_raw(con, "SELECT id FROM jobs")) == 1


def test_save_jobs_dedup_same_url():
    j1 = make_job(id="id1", job_url="http://same")
    j2 = make_job(id="id2", job_url="http://same")
    assert db.save_jobs([j1, j2]) == 1


def test_save_jobs_full_duplicate_batch():
    job = make_job()
    db.save_jobs([job])
    assert db.save_jobs([job]) == 0


def test_save_jobs_uses_job_url_when_id_missing():
    job = make_job(id=None, job_url="http://x/noid")
    db.save_jobs([job])
    with db._conn() as con:
        row = con.execute("SELECT id FROM jobs WHERE job_url = ?", ("http://x/noid",)).fetchone()
    assert row["id"] == "http://x/noid"


def test_get_unextracted_jobs_returns_eligible():
    db.save_jobs([make_job()])
    with db._conn() as con:
        con.execute("UPDATE jobs SET description_clean = 'cleaned' WHERE id = 'job1'")
    rows = db.get_unextracted_jobs()
    assert len(rows) == 1
    assert rows[0]["id"] == "job1"


def test_get_unextracted_jobs_excludes_null_description_clean():
    db.save_jobs([make_job()])
    assert db.get_unextracted_jobs() == []


def test_get_unextracted_jobs_excludes_already_extracted():
    db.save_jobs([make_job()])
    with db._conn() as con:
        con.execute("UPDATE jobs SET description_clean = 'cleaned' WHERE id = 'job1'")
    db.update_extracted_fields("job1", ["Python"], ["Build models"])
    assert db.get_unextracted_jobs() == []


def test_update_extracted_fields_roundtrip():
    db.save_jobs([make_job()])
    db.update_extracted_fields("job1", ["Python", "SQL"], ["Build models"])
    with db._conn() as con:
        row = con.execute("SELECT qualifications, responsibilities FROM jobs WHERE id = 'job1'").fetchone()
    assert json.loads(row["qualifications"]) == ["Python", "SQL"]
    assert json.loads(row["responsibilities"]) == ["Build models"]


def test_update_extracted_fields_empty_list():
    db.save_jobs([make_job()])
    db.update_extracted_fields("job1", [], [])
    with db._conn() as con:
        row = con.execute("SELECT qualifications FROM jobs WHERE id = 'job1'").fetchone()
    assert row["qualifications"] == "[]"
    # Not NULL, so not returned by get_unextracted_jobs
    assert db.get_unextracted_jobs() == []
    # But IS returned by get_jobs_missing_qual_meta (qualifications IS NOT NULL, max_yoe IS NULL)
    assert len(db.get_jobs_missing_qual_meta()) == 1


def test_get_jobs_missing_qual_meta_returns_eligible():
    db.save_jobs([make_job()])
    db.update_extracted_fields("job1", ["Python"], ["Build"])
    rows = db.get_jobs_missing_qual_meta()
    assert len(rows) == 1
    assert rows[0]["id"] == "job1"


def test_get_jobs_missing_qual_meta_excluded_after_update():
    db.save_jobs([make_job()])
    db.update_extracted_fields("job1", ["Python"], ["Build"])
    db.update_qual_meta("job1", 5, "MS")
    assert db.get_jobs_missing_qual_meta() == []


def test_get_jobs_missing_embedding_only_qualifications():
    db.save_jobs([make_job()])
    db.update_extracted_fields("job1", ["Python"], [])
    rows = db.get_jobs_missing_embedding()
    assert len(rows) == 1


def test_get_jobs_for_indexing():
    db.save_jobs([make_job()])
    assert db.get_jobs_for_indexing() == []
    blob = np.array([0.1, 0.2], dtype=np.float32).tobytes()
    db.update_jd_embedding("job1", blob)
    rows = db.get_jobs_for_indexing()
    assert len(rows) == 1
    assert rows[0]["id"] == "job1"


def test_search_jobs_keyword_title():
    db.save_jobs([make_job(title="Machine Learning Engineer")])
    results = db.search_jobs("machine")
    assert len(results) == 1


def test_search_jobs_keyword_description_clean():
    db.save_jobs([make_job()])
    with db._conn() as con:
        con.execute("UPDATE jobs SET description_clean = 'transformer architecture' WHERE id = 'job1'")
    results = db.search_jobs("transformer")
    assert len(results) == 1


def test_search_jobs_no_filter_returns_all():
    db.save_jobs([
        make_job(id="a", job_url="http://x/a", description="desc a"),
        make_job(id="b", job_url="http://x/b", description="desc b"),
        make_job(id="c", job_url="http://x/c", description="desc c"),
    ])
    assert len(db.search_jobs()) == 3


def test_search_jobs_hours_filter_excludes_old():
    db.save_jobs([make_job()])
    with db._conn() as con:
        con.execute("UPDATE jobs SET scraped_at = datetime('now', '-2 hours') WHERE id = 'job1'")
    assert db.search_jobs(hours=1) == []


def test_save_jobs_dedup_same_description():
    j1 = make_job(id="job1", job_url="http://x/1", description="identical desc")
    j2 = make_job(id="job2", job_url="http://x/2", description="identical desc")
    assert db.save_jobs([j1, j2]) == 1


def test_save_jobs_different_descriptions_both_saved():
    j1 = make_job(id="job1", job_url="http://x/1", description="desc A")
    j2 = make_job(id="job2", job_url="http://x/2", description="desc B")
    assert db.save_jobs([j1, j2]) == 2


def test_save_jobs_null_description_not_blocked():
    j1 = make_job(id="job1", job_url="http://x/1", description=None)
    j2 = make_job(id="job2", job_url="http://x/2", description=None)
    assert db.save_jobs([j1, j2]) == 2
