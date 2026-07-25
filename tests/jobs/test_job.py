import logging

import pytest
from pydantic import ValidationError

from immich2gpx.jobs.job import Job
from immich2gpx.models.asset import Asset
from immich2gpx.models.filter import Filter
from immich2gpx.models.query import Query


@pytest.fixture
def sample_config():
    return {
        "merge_jobs": "job1",
        "run_jobs": ["job2", "job3"],
        "filter": {"and": {"tag": 1, "color": "red"}},
    }


def test_job_config(sample_config):
    job = Job(sample_config, "job")
    assert job.config.merge_jobs == [sample_config["merge_jobs"]]
    assert job.config.run_jobs == sample_config["run_jobs"]
    assert job.merge_job_names == []
    assert job.run_job_names == []


def test_empty_job_name(sample_config):
    with pytest.raises(ValueError):
        Job(sample_config, "")


def test_invalid_job_name(sample_config):
    with pytest.raises(ValueError):
        Job(sample_config, "*")


def test_invalid_job_config_type():
    with pytest.raises(ValidationError):
        Job([], "job")  # type: ignore


def test_empty_job_config(caplog):
    caplog.set_level(logging.WARNING)
    Job({}, "job")
    assert "not configured" in caplog.text


def test_sub_job_nolist():
    with pytest.raises(ValidationError):
        Job({"merge_jobs": 123}, "job")


def test_sub_job_nostr():
    with pytest.raises(ValidationError):
        Job({"merge_jobs": [123]}, "job")


def test_sub_job_empty():
    job = Job({"merge_jobs": None}, "job")
    assert job.config.merge_jobs == []


def test_sub_job_config(sample_config):
    job = Job(sample_config, "job")
    assert job.config.merge_jobs == ["job1"]
    assert job.config.run_jobs == ["job2", "job3"]


def test_valid_filter(sample_config):
    job = Job(sample_config, "job")
    assert len(job.queries) == 1
    assert job.queries[0].filter.conditions == sample_config["filter"]["and"]


@pytest.fixture
def sample_results():
    return [
        Query(
            filter=Filter(conditions={"condition1": 1}),
            assets=[Asset(response={"id": "1"})],
        ),
        Query(
            filter=Filter(conditions={"condition2": 2}),
            assets=[Asset(response={"id": "2"})],
        ),
    ]


def test_merge_query(sample_config, sample_results):
    job1 = Job(sample_config, "job1")
    job2 = Job(sample_config, "job2")
    job3 = Job(sample_config, "job3")
    job1.queries = [sample_results[0]]
    job2.queries = [sample_results[1]]
    job3.queries = [sample_results[1]]
    job1.merge_queries(job2)
    job1.merge_queries(job3)
    assert len(job1.queries) == 2  # noqa: PLR2004
    assert job1.queries[0].assets == sample_results[0].assets
    assert job1.queries[1].assets == sample_results[1].assets


def test_get_items(sample_config, sample_results):
    job = Job(sample_config, "job1")
    job.queries = sample_results
    assert job.get_all_assets() == [a for q in sample_results for a in q.assets]
