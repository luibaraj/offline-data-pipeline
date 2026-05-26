import json
import numpy as np
import pytest
import chromadb
import config
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


def _insert_with_embedding(job_id="j1", scraped_at=None):
    db.save_jobs([make_job(id=job_id, job_url=f"http://x/{job_id}")])
    blob = np.array([0.1, 0.2, 0.3], dtype=np.float32).tobytes()
    with db._conn() as con:
        con.execute(
            "UPDATE jobs SET description_clean='c', qualifications='[\"Python\"]', "
            "responsibilities='[\"Build\"]', jd_embedding=? WHERE id=?",
            (blob, job_id),
        )
        if scraped_at:
            con.execute("UPDATE jobs SET scraped_at=? WHERE id=?", (scraped_at, job_id))


def test_build_index_empty_db(chroma_col):
    assert idx.build_index() == 0


def test_build_index_upserts_and_returns_count(chroma_col):
    _insert_with_embedding("j1")
    count = idx.build_index()
    assert count == 1
    result = chroma_col.get(ids=["j1"])
    assert result["ids"] == ["j1"]


def test_build_index_null_max_yoe_stored_as_minus_one(chroma_col):
    _insert_with_embedding("j1")
    idx.build_index()
    result = chroma_col.get(ids=["j1"], include=["metadatas"])
    assert result["metadatas"][0]["max_yoe"] == -1


def test_prune_stale_removes_orphan_id(chroma_col):
    chroma_col.upsert(
        ids=["orphan"],
        embeddings=[[0.1, 0.2, 0.3]],
        metadatas=[{"title": "ghost"}],
    )
    assert idx.prune_stale() == 1
    assert chroma_col.get(ids=["orphan"])["ids"] == []


def test_prune_stale_removes_old_vector(chroma_col):
    _insert_with_embedding("j1", scraped_at="2000-01-01 00:00:00")
    idx.build_index()
    assert idx.prune_stale(max_age_hours=24) == 1
    assert chroma_col.get(ids=["j1"])["ids"] == []


def test_prune_stale_keeps_fresh_vector(chroma_col):
    _insert_with_embedding("j1")
    idx.build_index()
    assert idx.prune_stale(max_age_hours=24) == 0
    assert chroma_col.get(ids=["j1"])["ids"] == ["j1"]


def test_prune_stale_empty_collection(chroma_col):
    assert idx.prune_stale() == 0


def test_prune_stale_removes_db_deleted_job(chroma_col):
    _insert_with_embedding("j1")
    idx.build_index()
    with db._conn() as con:
        con.execute("DELETE FROM jobs WHERE id = 'j1'")
    assert idx.prune_stale() == 1
    assert chroma_col.get(ids=["j1"])["ids"] == []
