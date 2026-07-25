import pytest

from immich2gpx.models.asset import Asset
from immich2gpx.models.filter import Filter
from immich2gpx.models.query import Query


@pytest.fixture
def sample_query():
    return Query(
        filter=Filter(conditions={"b": 2, "a": 1}),
        assets=[
            Asset(response={"id": 1, "dateTimeOriginal": "2026-01-01T12:00:00Z"}),
            Asset(response={"id": 2, "dateTimeOriginal": "2025-12-31T12:00:00+02:00"}),
        ],
    )


def test_defaults():
    q = Query()
    assert q.filter.conditions == {}
    assert q.assets == []


def test_init_filter():
    conditions = {"a": 1}
    q = Query(filter=Filter(conditions=conditions))
    assert q.filter.conditions == conditions


def test_init_invalid_filter():
    with pytest.raises(TypeError):
        Query(filter=[])  # type: ignore


def test_init_asset():
    response = {"id": 1}
    q = Query(assets=Asset(response=response))
    assert q.assets[0].response == response


def test_init_assets():
    response = {"id": 1}
    q = Query(assets=[Asset(response=response)])
    assert q.assets[0].response == response


def test_init_invalid_asset():
    with pytest.raises(TypeError):
        Query(assets={})  # type: ignore


def test_query_from_conditions(sample_query):
    conditions = sample_query.filter.conditions
    queries = Query.from_conditions({"and": conditions})
    assert len(queries) == 1
    assert queries[0].filter.conditions == sample_query.filter.conditions


def test_cache_key(sample_query):
    assert sample_query.cache_key() == (("a", 1), ("b", 2))


def test_compare_cache_key(sample_query):
    query = Query(filter=Filter(conditions={"a": 1, "b": 2}))
    assert query.compare_cache_key(sample_query)


def test_payload_defaults(sample_query):
    payload = sample_query.payload(page=3)
    assert payload["a"] == 1
    assert payload["b"] == 2  # noqa: PLR2004
    assert payload["order"] == "desc"
    assert payload["size"] == 250  # noqa: PLR2004
    assert payload["page"] == 3  # noqa: PLR2004
    assert payload["withExif"] is True
    assert payload["withPeople"] is True


def test_payload_preserves_existing_values():
    q = Query(filter=Filter(conditions={"order": "asc", "size": 50}))
    payload = q.payload(page=1)
    assert payload["order"] == "asc"
    assert payload["size"] == 50  # noqa: PLR2004
    assert payload["page"] == 1


def test_payload_does_not_modify_conditions(sample_query):
    query = sample_query
    cache = query.cache_key()
    query.payload(123)
    assert cache == query.cache_key()


def test_sort_assets_by_timestamp(sample_query):
    sample_query.sort_assets_by_timestamp()
    assert [a.extract_key("id") for a in sample_query.assets] == [2, 1]


def test_str_representation(sample_query):
    s = str(sample_query)
    assert "'b' = '2'" in s
    assert "'a' = '1'" in s
    assert " AND " in s
