import pytest

from immich2gpx.jobs.container import Container
from immich2gpx.models.asset import Asset
from immich2gpx.models.filter import Filter
from immich2gpx.models.query import Query


def test_invalid_job_config_type():
    with pytest.raises(TypeError):
        Container(123, "job")  # type: ignore


def test_empty_job_config():
    with pytest.raises(ValueError):
        Container({}, "job")


def test_empty_job_name():
    with pytest.raises(ValueError):
        Container({}, "")


@pytest.fixture
def sample_config():
    return {
        "job1": {"merge_jobs": ["job4", "job5"], "run_jobs": "job2"},
        "job2": {},
        "job3": {"run_jobs": ["job2", "job5"]},
        "job4": {"merge_jobs": "job5", "run_jobs": "job3"},
        "job5": {},
        "job6": {},
    }


def test_dfs_config(sample_config):
    cont = Container(sample_config, "job1")
    assert cont.config == sample_config
    assert cont.name == "job1"
    order = ["job5", "job2", "job3", "job4", "job1"]
    for i, key in enumerate(cont.jobs):
        assert key == order[i]
    standalone = [True, True, True, False, True]
    assert [cont.jobs[f"job{i}"].standalone for i in range(1, 6)] == standalone


def test_dfs_config_list(sample_config):
    jobs = [{key: value} for key, value in sample_config.items()]
    cont = Container(jobs, "job1")  # type: ignore
    assert cont.name == "job1"
    order = ["job5", "job2", "job3", "job4", "job1"]
    for i, key in enumerate(cont.jobs):
        assert key == order[i]


def test_dfs_recursion():
    conf = {
        "job1": {"run_jobs": "job2"},
        "job2": {"run_jobs": "job1"},
    }
    with pytest.raises(RecursionError):
        Container(conf, "job1")


def test_expression_mapping():
    conf = {
        "main": {"run_jobs": "job*"},
        "job1": {},
        "job2": {},
        "unused": {},
    }
    cont = Container(conf, "main")
    order = ["job1", "job2", "main"]
    for i, key in enumerate(cont.jobs):
        assert key == order[i]


def test_merge_jobs(sample_config):
    cont = Container(sample_config, "job1")
    queries = [
        Query(filter=Filter(conditions={"a": 1}), assets=[Asset(response={"id": 1})])
    ]
    cont.jobs["job4"].queries = queries
    cont.merge_sub_jobs("job1")
    assert "job4" in cont.jobs["job1"].merge_job_names
    assert cont.jobs["job1"].queries == queries


def test_merge_invalid_name(sample_config):
    cont = Container(sample_config, "job1")
    with pytest.raises(ValueError):
        cont.merge_sub_jobs("invalid")


def test_merge_invalid_subname(sample_config):
    cont = Container(sample_config, "job1")
    cont.jobs["job1"].merge_job_names = ["invalid"]
    with pytest.raises(ValueError):
        cont.merge_sub_jobs("job1")
