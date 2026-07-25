import logging
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from immich2gpx.config.loader import ConfigLoader


def test_missing_file(tmp_path: Path):
    file = tmp_path / "file.yaml"
    with pytest.raises(FileNotFoundError):
        ConfigLoader.load(file)


def test_is_not_file(tmp_path: Path):
    with pytest.raises(ValueError):
        ConfigLoader.load(tmp_path)


def test_loader(tmp_path: Path, caplog):
    file = tmp_path / "file.yaml"
    file.write_text("key: value")
    data = ConfigLoader._load_yaml(file)
    assert str(file) in caplog.text
    assert "key" in data


def test_included_config(tmp_path: Path):
    file1 = tmp_path / "file1.yaml"
    file1.write_text("!include file2.yaml")
    file2 = tmp_path / "file2.yaml"
    file2.write_text("tag: !include file3.yaml")
    file3 = tmp_path / "file3.yaml"
    file3.write_text("key: value")
    data = ConfigLoader._load_yaml(file1)
    assert data["tag"] == {"key": "value"}


def test_invalid_include(tmp_path: Path):
    file = tmp_path / "file.yaml"
    file.write_text("!include ../file.yaml")
    with pytest.raises(ValueError):
        ConfigLoader._load_yaml(file)


def test_invalid_reference_config():
    with pytest.raises(TypeError):
        ConfigLoader._resolve([])  # type: ignore


def test_invalid_reference_dict():
    with pytest.raises(TypeError):
        ConfigLoader._resolve({1: 2})  # type: ignore


def test_empty_reference(caplog):
    caplog.set_level(logging.WARNING)
    ConfigLoader._resolve({})
    assert "is empty" in caplog.text


def test_simple_reference():
    config = {
        "references": {"a": {"tag": 1}},
        "jobs": {"j": {"and": [{"ref": "a"}, {"tag": 2}]}},
    }
    resolved = ConfigLoader._resolve(config)
    assert resolved["jobs"]["j"]["and"] == [{"tag": 1}, {"tag": 2}]


def test_none_reference():
    config = {"references": None}
    resolved = ConfigLoader._resolve(config)
    assert resolved["references"] == {}


def test_list_none_reference():
    config = {
        "references": [None],
    }
    resolved = ConfigLoader._resolve(config)
    assert resolved["references"] == [{}]


def test_list_reference():
    config = {
        "references": [{"a": {"tag": 1}}],
        "jobs": {"j": {"and": [{"ref": "a"}, {"tag": 2}]}},
    }
    resolved = ConfigLoader._resolve(config)
    assert resolved["jobs"]["j"]["and"] == [{"tag": 1}, {"tag": 2}]


def test_local_and_global_references():
    config = {
        "references": {"a": {"tag": 1}},
        "jobs": {
            "j1": {
                "references": {"b": {"tag": 2}},
                "and": [{"ref": "a"}, {"ref": "b"}],
            },
            "j2": {"references": {"b": {"tag": 3}}, "and": {"ref": "b"}},
        },
    }
    resolved = ConfigLoader._resolve(config)
    assert resolved["jobs"]["j1"]["and"] == [{"tag": 1}, {"tag": 2}]
    assert resolved["jobs"]["j2"]["and"] == {"tag": 3}


def test_nested_reference():
    config = {
        "references": {"a": {"tag": 1}, "b": {"ref": "a"}},
        "jobs": {"j": {"ref": "b"}},
    }
    resolved = ConfigLoader._resolve(config)
    assert resolved["jobs"]["j"] == {"tag": 1}


def test_invalid_references_type():
    config = {"references": [[{"a": {"tag": 1}}]]}
    with pytest.raises(TypeError):
        ConfigLoader._resolve(config)


def test_duplicate_reference():
    config = {
        "references": {"a": {"tag": 1}},
        "jobs": {
            "j1": {"references": {"a": {"tag": 2}}},
        },
    }
    with pytest.raises(ValueError):
        ConfigLoader._resolve(config)


def test_circular_reference():
    config = {
        "references": {"a": {"ref": "b"}, "b": {"ref": "a"}},
    }
    with pytest.raises(RecursionError):
        ConfigLoader._resolve(config)


def test_unknown_reference():
    config = {
        "references": {"a": {"tag": 1}},
        "ref": "b",
    }
    with pytest.raises(KeyError):
        ConfigLoader._resolve(config)


def test_empty_load(tmp_path: Path):
    file = tmp_path / "file.yaml"
    file.write_text("")
    data = ConfigLoader.load(file).model_dump()
    assert "immich" in data
    assert "analysis" in data
    assert "gpx" in data
    assert "jobs" in data


def test_load_invalid_data(tmp_path: Path):
    file = tmp_path / "file.yaml"
    file.write_text("key: value")
    with pytest.raises(ValidationError):
        ConfigLoader.load(file)


def test_config_datatypes(tmp_path: Path):
    file = tmp_path / "file.yaml"
    config = [
        "references:",
        "  key_string1: test string 1",
        '  key_string2: "test string 2"',
        "  key_int: 5",
        "  key_float: 1.2",
        "  key_datetime: 2025-06-15T12:34:56",
        "  key_true: true",
        "  key_false: false",
        "  key_null: null",
        "  key_list1:",
        "    - 'entry'",
        "  key_list2:",
        "    [",
        "        'entry1',",
        "        'entry2',",
        "    ]",
    ]
    file.write_text("\n".join(config))
    data = ConfigLoader.load(file).model_dump()["references"]
    assert data["key_string1"] == "test string 1"
    assert data["key_string2"] == "test string 2"
    assert data["key_int"] == 5  # noqa: PLR2004
    assert data["key_float"] == 1.2  # noqa: PLR2004
    assert data["key_datetime"] == datetime(2025, 6, 15, 12, 34, 56)  # noqa: DTZ001
    assert data["key_true"] == True  # noqa: E712
    assert data["key_false"] == False  # noqa: E712
    assert data["key_null"] == {}
    assert data["key_list1"] == ["entry"]
    assert data["key_list2"] == ["entry1", "entry2"]
