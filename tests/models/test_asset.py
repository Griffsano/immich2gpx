import logging
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from immich2gpx.models.asset import Asset


def test_asset_valid_empty_default():
    asset = Asset()
    assert asset.response == {}


def test_asset_invalid_response_type():
    with pytest.raises(ValidationError):
        Asset(response=123)  # type: ignore


def test_extract_key_from_response():
    asset = Asset(response={"id": "123"})
    assert asset.extract_key("id") == "123"


def test_extract_key_from_exif():
    asset = Asset(response={"exifInfo": {"dateTimeOriginal": "2024-01-01T10:00:00Z"}})
    assert asset.extract_key("dateTimeOriginal") == "2024-01-01T10:00:00Z"


def test_extract_key_missing():
    asset = Asset(response={})
    assert asset.extract_key("missing") is None


def test_parse_timestamp_valid_iso_with_z():
    asset = Asset(response={"dateTimeOriginal": "2024-01-01T10:00:00Z"})
    ts = asset._parse_timestamp("dateTimeOriginal")
    assert ts == datetime.fromisoformat("2024-01-01T10:00:00+00:00")


def test_parse_timestamp_timezone():
    asset = Asset(response={"dateTimeOriginal": "2024-01-01T10:00:00-05:00"})
    ts = asset._parse_timestamp("dateTimeOriginal")
    assert ts
    assert ts.tzinfo is not None
    assert ts.tzinfo.utcoffset(ts) == timedelta(hours=-5)


def test_parse_timestamp_invalid_logs_warning(caplog):
    asset = Asset(response={"dateTimeOriginal": "invalid-timestamp"})
    with caplog.at_level(logging.WARNING):
        ts = asset._parse_timestamp("dateTimeOriginal")
    assert "does not have a valid" in caplog.text
    assert ts is None


def test_get_timestamp_parses_and_caches():
    asset = Asset(response={"dateTimeOriginal": "2024-01-01T10:00:00Z"})
    ts1 = asset.get_timestamp()
    ts2 = asset.get_timestamp()
    assert ts1 == ts2
    assert asset._timestamp == ts1


def test_get_timestamp_when_already_set():
    preset = datetime(2023, 1, 1, tzinfo=timezone.utc)
    asset = Asset(response={})
    asset._timestamp = preset
    assert asset.get_timestamp() == preset


def test_str_representation():
    asset = Asset(response={"id": "123", "originalFileName": "image.jpg"})
    s = str(asset)
    assert "id=123" in s
    assert "originalFileName=image.jpg" in s
