import json
import numpy as np
import pytest
import chromadb
import storage.db as db
import storage.index as idx
from conftest import make_job


@pytest.fixture
def chroma_col(monkeypatch):
    client = chromadb.EphemeralClient(settings=chromadb.Settings(allow_reset=True))
    client.reset()
    col = client.get_or_create_collection(
        "job_descriptions", metadata={"hnsw:space": "cosine"}
    )
    monkeypatch.setattr("storage.index._get_collection", lambda: col)
    yield col
    client.reset()


def test_preprocess_to_extract_handoff():
    db.save_jobs([make_job()])
    assert db.get_unextracted_jobs() == []

    with db._conn() as con:
        con.execute("UPDATE jobs SET description_clean = 'cleaned text' WHERE id = 'job1'")

    assert len(db.get_unextracted_jobs()) == 1

    db.update_extracted_fields("job1", ["Python"], ["Build models"])
    assert db.get_unextracted_jobs() == []


def test_extract_to_qual_meta_handoff():
    db.save_jobs([make_job()])
    db.update_extracted_fields("job1", ["5+ years Python"], ["Build models"])

    assert len(db.get_jobs_missing_qual_meta()) == 1

    db.update_qual_meta("job1", 5, "MS")
    db.update_is_internship("job1", False)
    assert db.get_jobs_missing_qual_meta() == []


def test_qual_meta_to_embed_handoff():
    db.save_jobs([make_job()])
    db.update_extracted_fields("job1", ["Python"], ["Build models"])

    assert len(db.get_jobs_missing_embedding()) == 1

    blob = np.array([0.1, 0.2, 0.3], dtype=np.float32).tobytes()
    db.update_jd_embedding("job1", blob)

    assert db.get_jobs_missing_embedding() == []


def test_embed_to_index_roundtrip(chroma_col):
    db.save_jobs([make_job()])
    db.update_extracted_fields("job1", ["Python"], ["Build models"])
    blob = np.array([0.1, 0.2, 0.3], dtype=np.float32).tobytes()
    db.update_jd_embedding("job1", blob)

    assert len(db.get_jobs_for_indexing()) == 1
    assert idx.build_index() == 1
    assert chroma_col.get(ids=["job1"])["ids"] == ["job1"]
    assert idx.prune_stale(max_age_hours=24) == 0


def test_duplicate_suppression_end_to_end():
    job = make_job()
    count = db.save_jobs([job, job])
    assert count == 1
    with db._conn() as con:
        rows = con.execute("SELECT id FROM jobs").fetchall()
    assert len(rows) == 1
