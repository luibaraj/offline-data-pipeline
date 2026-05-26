import pandas as pd
import pytest
import config
from scraper.scraper import _check_proxy, scrape_paginated


def make_df(n, start=0):
    return pd.DataFrame([
        {
            "id": str(i), "job_url": f"http://x/{i}", "title": "T",
            "company": "C", "location": "L", "description": "D", "date_posted": "2024-01-01",
        }
        for i in range(start, start + n)
    ])


def test_check_proxy_raises_after_all_failures(mocker):
    mocker.patch("scraper.scraper.requests.head", side_effect=ConnectionError("timeout"))
    with pytest.raises(RuntimeError, match="Proxy unreachable"):
        _check_proxy("http://proxy:8080")


def test_check_proxy_succeeds_on_second_attempt(mocker):
    mock_head = mocker.patch(
        "scraper.scraper.requests.head",
        side_effect=[ConnectionError("fail"), None],
    )
    _check_proxy("http://proxy:8080")  # should not raise
    assert mock_head.call_count == 2


def test_scrape_paginated_early_stop_on_partial_batch(mocker, monkeypatch):
    monkeypatch.setattr(config, "PROXY_URL", None)
    mock_scrape = mocker.patch("scraper.scraper.scrape_jobs", return_value=make_df(5))
    mock_sleep = mocker.patch("scraper.scraper.time.sleep")

    results = scrape_paginated("MLE", "US", total=25)

    assert mock_scrape.call_count == 1
    assert len(results) == 5
    mock_sleep.assert_not_called()


def test_scrape_paginated_no_proxy_skips_check(mocker, monkeypatch):
    monkeypatch.setattr(config, "PROXY_URL", None)
    mocker.patch("scraper.scraper.scrape_jobs", return_value=make_df(5))
    mocker.patch("scraper.scraper.time.sleep")
    mock_head = mocker.patch("scraper.scraper.requests.head")

    scrape_paginated("MLE", "US", total=25)

    mock_head.assert_not_called()


def test_scrape_paginated_jitter_between_batches_only(mocker, monkeypatch):
    monkeypatch.setattr(config, "PROXY_URL", None)
    mocker.patch(
        "scraper.scraper.scrape_jobs",
        side_effect=[make_df(25, start=0), make_df(5, start=25)],
    )
    mock_sleep = mocker.patch("scraper.scraper.time.sleep")

    results = scrape_paginated("MLE", "US", total=50)

    assert mock_sleep.call_count == 1
    assert len(results) == 30


def test_scrape_paginated_returns_all_results(mocker, monkeypatch):
    monkeypatch.setattr(config, "PROXY_URL", None)
    mocker.patch(
        "scraper.scraper.scrape_jobs",
        side_effect=[make_df(25, start=0), make_df(25, start=25)],
    )
    mocker.patch("scraper.scraper.time.sleep")

    results = scrape_paginated("MLE", "US", total=50)

    assert len(results) == 50
