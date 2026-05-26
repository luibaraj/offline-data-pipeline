import os
import pytest
import config
import storage.db as db

os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("VOYAGE_API_KEY", "test-key")


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test.db"))
    db.init()
    yield


def make_job(id="job1", job_url="http://x/1", title="MLE", **kwargs):
    return {
        "id": id,
        "job_url": job_url,
        "title": title,
        "company": "Acme",
        "location": "US",
        "description": "raw desc",
        "date_posted": "2024-01-01",
        **kwargs,
    }
