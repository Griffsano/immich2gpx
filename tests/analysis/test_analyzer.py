"""Tests for the Analyzer."""

import logging

import pytest
from pydantic import ValidationError

from immich2gpx.analysis.analyzer import Analyzer
from immich2gpx.models.asset import Asset


def test_invalid_analyzer_config_type():
    with pytest.raises(ValidationError):
        Analyzer([])  # type: ignore


def test_empty_analyzer_config():
    writer = Analyzer({"group_by_keys": None})
    assert writer.config.show_keys == []
    assert writer.config.group_by_keys == []


def test_empty_keys_in_config(caplog):
    caplog.set_level(logging.WARNING)
    writer = Analyzer({})
    writer.show([])
    writer.group([])
    assert "Showing no assets" in caplog.text
    assert "Showing no groups" in caplog.text


def test_analyzer_additional_keys():
    with pytest.raises(ValidationError):
        Analyzer({"some_other_keys": "id"})


def test_analyzer_nolist():
    with pytest.raises(ValidationError):
        Analyzer({"show_keys": 123})


def test_analyzer_nostr():
    with pytest.raises(ValidationError):
        Analyzer({"show_keys": ["valid", 42]})


def test_analyzer_single_str():
    writer = Analyzer({"show_keys": "id"})
    assert writer.config.show_keys == ["id"]


@pytest.fixture
def sample_config():
    return {
        "show_keys": ["file", "float"],
        "group_by_keys": "tag",
    }


def test_analyzer_config(sample_config):
    analyzer = Analyzer(sample_config)
    assert analyzer.config.show_keys == sample_config["show_keys"]
    assert analyzer.config.group_by_keys == [sample_config["group_by_keys"]]


@pytest.fixture
def sample_show():
    return [
        Asset(
            response={
                "file": "a",
                "int": 1,
                "exifInfo": {"str": "test", "float": 2},
            }
        ),
        Asset(
            response={
                "file": "b",
            }
        ),
    ]


def test_show_log(caplog, sample_config, sample_show):
    Analyzer(sample_config).show(sample_show)
    assert "file" in caplog.text
    assert "float" in caplog.text
    assert "int" not in caplog.text


def test_show_metadata(sample_config, sample_show):
    result = Analyzer(sample_config).show(sample_show)
    assert result == [{"file": "a", "float": 2}, {"file": "b", "float": None}]


@pytest.fixture
def sample_group():
    return [
        Asset(response={"file": "a", "tag": "x"}),
        Asset(response={"file": "b", "exifInfo": {"tag": "x"}}),
        Asset(response={"file": "c"}),
    ]


def test_group_log(caplog, sample_config, sample_group):
    Analyzer(sample_config).group(sample_group)
    assert "tag" in caplog.text
    assert "file" in caplog.text


def test_group_metadata(sample_config, sample_group):
    sample_config["group_by_keys"] = [sample_config["group_by_keys"], "nonexisting"]
    result = Analyzer(sample_config).group(sample_group)
    assert result == {
        (("tag", "x"), ("nonexisting", None)): sample_group[0:2],
        (("tag", None), ("nonexisting", None)): sample_group[2:3],
    }


@pytest.fixture
def sample_job1():
    return [Asset(response={"id": "a"}), Asset(response={"id": "c"})]


@pytest.fixture
def sample_job2():
    return [Asset(response={"id": "b"}), Asset(response={"id": "c"})]


def test_compare_logs(caplog, sample_config, sample_job1, sample_job2):
    Analyzer(sample_config).compare(sample_job1, sample_job2)
    assert "assets present only in" in caplog.text
    assert "assets present in both" in caplog.text
    assert "file" in caplog.text
    assert "float" in caplog.text


def test_compare_metadata(sample_config, sample_job1, sample_job2):
    result = Analyzer(sample_config).compare(sample_job1, sample_job2)
    assert result == {
        "only_baseline": {"a"},
        "only_compare": {"b"},
        "both": {"c"},
    }


def test_compare_no_baseline_id(caplog, sample_config):
    result = Analyzer(sample_config).compare([Asset(response={"noid": 0})], [])
    assert "baseline assets without ID" in caplog.text
    assert "compare assets without ID" not in caplog.text
    assert result == {"only_baseline": set(), "only_compare": set(), "both": set()}


def test_compare_no_compare_id(caplog, sample_config):
    result = Analyzer(sample_config).compare([], [Asset(response={"noid": 0})])
    assert "baseline assets without ID" not in caplog.text
    assert "compare assets without ID" in caplog.text
    assert result == {"only_baseline": set(), "only_compare": set(), "both": set()}
