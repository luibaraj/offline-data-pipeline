import json
import logging
from datetime import datetime, timedelta, timezone

import numpy as np
from langchain_chroma import Chroma

import config
import storage.db as db

logger = logging.getLogger(__name__)

COLLECTION_NAME = "job_descriptions"


def _get_collection():
    store = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=config.CHROMA_PATH,
        embedding_function=None,
        collection_metadata={
            "hnsw:space": "cosine",
            "hnsw:construction_ef": 200,
            "hnsw:search_ef": 400,
        },
    )
    return store._collection


def build_index() -> int:
    rows = db.get_jobs_for_indexing()
    if not rows:
        logger.info("No jobs with embeddings found — nothing to index")
        return 0

    ids, embeddings, metadatas = [], [], []
    for row in rows:
        ids.append(row["id"])
        embeddings.append(np.frombuffer(row["jd_embedding"], dtype=np.float32).tolist())
        metadatas.append({
            "title": row["title"] or "",
            "company": row["company"] or "",
            "job_url": row["job_url"] or "",
            "max_yoe": row["max_yoe"] if row["max_yoe"] is not None else -1,
            "min_education": row["min_education"] or "",
            "responsibilities": json.dumps(json.loads(row["responsibilities"] or "[]")),
            "qualifications": json.dumps(json.loads(row["qualifications"] or "[]")),
            "is_internship": row["is_internship"] if row["is_internship"] is not None else -1,
        })

    _get_collection().upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)
    logger.info("Upserted %d vectors into ChromaDB", len(ids))
    return len(ids)


def prune_stale(max_age_hours: int = 24) -> int:
    collection = _get_collection()
    result = collection.get(include=["metadatas"])
    if not result["ids"]:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    rows_by_id = {row["id"]: row for row in db.get_jobs_for_indexing()}

    stale_ids = [
        chroma_id for chroma_id in result["ids"]
        if chroma_id not in rows_by_id
        or datetime.fromisoformat(rows_by_id[chroma_id]["scraped_at"]).replace(tzinfo=timezone.utc) < cutoff
    ]

    if stale_ids:
        collection.delete(ids=stale_ids)
        logger.info("Pruned %d stale vectors from ChromaDB", len(stale_ids))
    return len(stale_ids)
