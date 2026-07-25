import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from immich2gpx.export.gpxwriter import GPXWriter
from immich2gpx.models.asset import Asset
from immich2gpx.models.filter import Filter
from immich2gpx.models.query import Query


def test_invalid_gpx_config_type():
    with pytest.raises(ValidationError):
        GPXWriter([])  # type: ignore


def test_empty_gpx_config():
    writer = GPXWriter({})
    assert writer.config.directory == Path("gpx")
    assert writer.config.description_keys == []


def test_nonexisting_gpx_path(tmp_path):
    missing_path = tmp_path / "missing_path"
    with pytest.raises(FileNotFoundError):
        GPXWriter({"directory": str(missing_path)})


def test_file_as_gpx_path(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("content")
    with pytest.raises(NotADirectoryError):
        GPXWriter({"directory": str(file_path)})


def test_gpx_desc_nolist():
    with pytest.raises(ValidationError):
        GPXWriter({"description_keys": 123})


def test_gpx_desc_nostr():
    with pytest.raises(ValidationError):
        GPXWriter({"description_keys": ["valid", 42]})


def test_gpx_desc_empty():
    writer = GPXWriter({"description_keys": None})
    assert writer.config.description_keys == []


def test_gpx_desc_single_str():
    writer = GPXWriter({"description_keys": "id"})
    assert writer.config.description_keys == ["id"]


@pytest.fixture
def sample_config(tmp_path):
    return {
        "directory": str(tmp_path),
        "description_keys": ["id", "country", "invalid"],
    }


def test_gpx_config(sample_config):
    writer = GPXWriter(sample_config)
    assert str(writer.config.directory) == sample_config["directory"]
    assert writer.config.description_keys == sample_config["description_keys"]


@pytest.fixture
def sample_results():
    return [
        Query(
            filter=Filter(
                conditions={
                    "condition1": 1,
                }
            ),
            assets=[
                Asset(
                    response={
                        "id": "1",
                        "originalFileName": "1.jpg",
                        "exifInfo": {
                            "latitude": 2,
                            "longitude": 3.3,
                            "dateTimeOriginal": "1000-01-10T01:10:10+01:00",
                            "country": "country1",
                        },
                    }
                ),
                Asset(
                    response={
                        "id": "2",
                        "originalFileName": "2.jpg",
                        "exifInfo": {
                            "latitude": 20,
                            "longitude": 30.3,
                            "dateTimeOriginal": "2000-02-20T02:20:20+02:00",
                            "country": "country2",
                        },
                    }
                ),
            ],
        ),
        Query(
            filter=Filter(
                conditions={
                    "condition2": 2,
                    "condition3": 3,
                }
            ),
            assets=[
                Asset(
                    response={
                        "id": "3",
                        "originalFileName": "3.jpg",
                        "exifInfo": {
                            "latitude": 200,
                            "longitude": 300.3,
                            "dateTimeOriginal": "3000-03-30T03:30:30+03:00",
                            "country": "country3",
                        },
                    }
                )
            ],
        ),
    ]


def test_gpx_empty_job_name(sample_config, sample_results):
    writer = GPXWriter(sample_config)
    with pytest.raises(ValueError):
        writer.create("", sample_results)


def test_gpx_invalid_job_name(sample_config, sample_results):
    writer = GPXWriter(sample_config)
    with pytest.raises(ValueError):
        writer.create("*", sample_results)


def test_gpx_invalid_query(sample_config):
    with pytest.raises(TypeError):
        GPXWriter(sample_config).create("job", None)  # type: ignore


def test_gpx_writes_file(sample_config, sample_results):
    job_name = "job_name-1.2"
    path = Path(sample_config["directory"])
    file_path = path / (job_name + ".gpx")
    GPXWriter(sample_config).create(job_name, sample_results)
    assert file_path.exists()


def test_gpx_written_file(sample_config, sample_results):
    path = Path(sample_config["directory"])
    file_path = path / "job1.gpx"
    GPXWriter(sample_config).create("job1", sample_results)
    content = file_path.read_text(encoding="utf-8")
    for string in ["gpx", "trk", "trkseg"]:
        assert string in content
    for string in [f"condition{id}" for id in range(1, 3)]:
        assert string in content
    for string in ["id=", "invalid=None"]:
        assert string in content
    for string in [f"country=country{id}" for id in range(1, 4)]:
        assert string in content
    for string in [
        'lat="2" lon="3.3"',
        "1000-01-10T01:10:10+01:00",
    ]:
        assert string in content
    for string in ["originalFileName", "1.jpg"]:
        assert string not in content


def test_gpx_invalid_exif(caplog, sample_config, sample_results):
    caplog.set_level(logging.WARNING)
    sample_results[0].assets[0].response["exifInfo"]["latitude"] = "123"
    sample_results[1].assets[0].response["exifInfo"]["dateTimeOriginal"] = 123
    GPXWriter(sample_config).create("job1", sample_results)
    assert "1.jpg" in caplog.text
    assert "2.jpg" not in caplog.text
    assert "3.jpg" in caplog.text
