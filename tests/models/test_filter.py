from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from immich2gpx.models.filter import Filter


@pytest.fixture
def sample_filter():
    return Filter(conditions={"b": 2, "a": 1})


def test_defaults():
    f = Filter()
    assert f.conditions == {}


def test_sort_conditions(sample_filter):
    sample_filter._sort_conditions()
    assert list(sample_filter.conditions.keys()) == ["a", "b"]


def test_formatted_conditions_types():
    dt = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    filter = Filter(
        conditions={
            "none": None,
            "empty": {},
            "bool": True,
            "int": 1,
            "float": 1.5,
            "date": dt,
            "list": ["a", "b"],
            "str": "hello",
        }
    )
    formatted = filter.formatted_conditions
    assert formatted["none"] is None
    assert formatted["empty"] is None
    assert formatted["bool"] == True  # noqa: E712
    assert formatted["int"] == 1
    assert formatted["float"] == 1.5  # noqa: PLR2004
    assert formatted["date"] == dt.isoformat()
    assert "+00:00" in formatted["date"]
    assert formatted["list"] == ("a", "b")
    assert formatted["str"] == "hello"


def test_formatted_conditions_cached(sample_filter):
    first = sample_filter.formatted_conditions
    second = sample_filter.formatted_conditions
    assert first is second


def test_or_merging():
    filters = [Filter(conditions={"tag": 1}), Filter(conditions={"color": "red"})]
    merged = Filter._merge_or_conditions(filters)
    assert merged == filters


def test_or_merging_duplicates(caplog):
    filter = Filter(conditions={"tag": 1})
    merged = Filter._merge_or_conditions([filter, filter])
    assert "duplicate" in caplog.text
    assert merged == [filter]


def test_or_merging_first_smaller(caplog):
    filters = [
        Filter(conditions={"tag": 1}),
        Filter(conditions={"tag": 1, "color": "red"}),
    ]
    merged = Filter._merge_or_conditions(filters)
    assert "conservative" in caplog.text
    assert merged == [filters[0]]


def test_or_merging_second_smaller(caplog):
    filters = [
        Filter(conditions={"tag": 1, "color": "red"}),
        Filter(conditions={"tag": 1}),
    ]
    merged = Filter._merge_or_conditions(filters)
    assert "conservative" in caplog.text
    assert merged == [filters[1]]


def test_and_merging():
    filters = [Filter(conditions={"tag": 1}), Filter(conditions={"color": "red"})]
    merged = Filter._merge_and_conditions(filters)
    assert merged == Filter(conditions={"tag": 1, "color": "red"})


def test_and_merging_duplicates(caplog):
    filter = Filter(conditions={"tag": 1})
    merged = Filter._merge_and_conditions([filter, filter])
    assert "Duplicate key" in caplog.text
    assert merged == filter


def test_and_conflicting_duplicates():
    filters = [Filter(conditions={"tag": 1}), Filter(conditions={"tag": 2})]
    with pytest.raises(ValueError):
        Filter._merge_and_conditions(filters)


def test_invalid_normalization_type():
    with pytest.raises(TypeError):
        Filter._normalize_conditions("invalid", True)  # type: ignore


def test_invalid_normalization_dict():
    with pytest.raises(ValidationError):
        Filter._normalize_conditions({1: 2}, True)  # type: ignore


def dnf_to_condition_list(dnf: list[Filter]):
    return [d.conditions for d in dnf]


def test_or_dict_normalization():
    condition = {"tag": 1, "color": "red"}
    dnf = Filter._normalize_conditions(condition, True)
    assert dnf_to_condition_list(dnf) == [{"tag": 1}, {"color": "red"}]


def test_and_dict_normalization():
    condition = {"tag": 1, "color": "red"}
    dnf = Filter._normalize_conditions(condition, False)
    assert dnf_to_condition_list(dnf) == [condition]


def test_or_list_normalization():
    conditions = [{"tag": 1}, {"color": "red"}]
    dnf = Filter._normalize_conditions(conditions, True)
    assert dnf_to_condition_list(dnf) == conditions


def test_and_list_normalization():
    conditions = [{"tag": 1}, {"color": "red"}]
    dnf = Filter._normalize_conditions(conditions, False)
    assert dnf_to_condition_list(dnf) == [{"tag": 1, "color": "red"}]


def test_normalization_sorting():
    condition = {"tag": 1, "color": "red"}
    dnf = Filter._normalize_conditions(condition, False)
    assert list(dnf[0].conditions)[0] == "color"  # noqa: RUF015
    assert list(dnf[0].conditions)[1] == "tag"


def test_invalid_filter_type():
    with pytest.raises(TypeError):
        Filter.parse_filter([])  # type: ignore


def test_invalid_filter_contents():
    with pytest.raises(TypeError):
        Filter.parse_filter({1: 1})  # type: ignore


def test_both_and_or_filter():
    condition = {"aNd": 1, "Or": 2}
    with pytest.raises(ValueError):
        Filter.parse_filter(condition)


def test_empty_filter(caplog):
    queries = Filter.parse_filter({})
    assert "No media file filter" in caplog.text
    assert queries == []


def test_invalid_filter():
    with pytest.raises(ValueError):
        Filter.parse_filter({"key": 0})


def test_distribution_normalization():
    # A AND (B OR C) =
    # (A AND B) OR (A AND C)
    condition = {"and": [{"a": 1}, {"or": [{"b": 2}, {"c": 3}]}]}
    dnf = Filter.parse_filter(condition)
    assert dnf_to_condition_list(dnf) == [{"a": 1, "b": 2}, {"a": 1, "c": 3}]


def test_flattening_normalization():
    # A AND (B OR (C AND D)) =
    # (A AND B) OR (A AND C AND D)
    condition = {"and": [{"a": 1}, {"or": [{"b": 2}, {"and": [{"c": 3}, {"d": 4}]}]}]}
    dnf = Filter.parse_filter(condition)
    assert dnf_to_condition_list(dnf) == [{"a": 1, "b": 2}, {"a": 1, "c": 3, "d": 4}]


def test_extended_distribution():
    # (A AND B) AND (C OR D) =
    # (A AND B AND C) OR (A AND B AND D)
    condition = {"and": {"and": {"a": 1, "b": 2}, "or": {"c": 3, "d": 4}}}
    dnf = Filter.parse_filter(condition)
    assert dnf_to_condition_list(dnf) == [
        {"a": 1, "b": 2, "c": 3},
        {"a": 1, "b": 2, "d": 4},
    ]


def test_complex_distribution():
    # ((A AND B) OR (C AND (D OR E))) AND ((F AND G) OR (H AND (I OR J))) =
    # ((A AND B AND F AND G) OR (A AND B AND H AND I) OR (A AND B AND H AND J) OR
    # (C AND D AND F AND G) OR (C AND D AND H AND I) OR (C AND D AND H AND J) OR
    # (C AND E AND F AND G) OR (C AND E AND H AND I) OR (C AND E AND H AND J))
    condition = {
        "and": [
            {
                "or": [
                    {"and": [{"a": "a"}, {"b": "b"}]},
                    {"and": [{"c": "c"}, {"or": [{"d": "d"}, {"e": "e"}]}]},
                ]
            },
            {
                "or": [
                    {"and": [{"f": "f"}, {"g": "g"}]},
                    {"and": [{"h": "h"}, {"or": [{"i": "i"}, {"j": "j"}]}]},
                ]
            },
        ]
    }
    dnf = Filter.parse_filter(condition)
    assert dnf_to_condition_list(dnf) == [
        {"a": "a", "b": "b", "f": "f", "g": "g"},
        {"a": "a", "b": "b", "h": "h", "i": "i"},
        {"a": "a", "b": "b", "h": "h", "j": "j"},
        {"c": "c", "d": "d", "f": "f", "g": "g"},
        {"c": "c", "d": "d", "h": "h", "i": "i"},
        {"c": "c", "d": "d", "h": "h", "j": "j"},
        {"c": "c", "e": "e", "f": "f", "g": "g"},
        {"c": "c", "e": "e", "h": "h", "i": "i"},
        {"c": "c", "e": "e", "h": "h", "j": "j"},
    ]


def test_complex_simplification():
    # ((A AND B) OR (C AND (A AND B))) AND ((A AND B) OR (A OR B)) =
    # A AND B
    condition = {
        "and": [
            {
                "or": [
                    {"and": [{"a": "a"}, {"b": "b"}]},
                    {"and": [{"c": "c"}, {"and": [{"a": "a"}, {"b": "b"}]}]},
                ]
            },
            {
                "or": [
                    {"and": [{"a": "a"}, {"b": "b", "a": "a"}]},
                    {"or": [{"a": "a"}, {"b": "b", "a": "a"}]},
                ]
            },
        ]
    }
    dnf = Filter.parse_filter(condition)
    assert dnf_to_condition_list(dnf) == [{"a": "a", "b": "b"}]


def test_str_representation(sample_filter):
    assert str(sample_filter) == "'b' = '2' AND 'a' = '1'"
