import copy
import json
from unittest.mock import MagicMock

import pytest
import requests
from pydantic import HttpUrl, ValidationError

from immich2gpx.immich.client import ImmichClient
from immich2gpx.immich.responses import AssetsResponse
from immich2gpx.models.asset import Asset
from immich2gpx.models.filter import Filter
from immich2gpx.models.query import Query


@pytest.fixture
def sample_config():
    return {
        "url": "https://demo.immich.app",
        "api_key": "apiKey",
        "timeout": 10,
    }


def test_immich_config(sample_config):
    client = ImmichClient(sample_config, True)
    assert client.config.url == HttpUrl(sample_config["url"] + "/api")
    assert client.config.headers == {"x-api-key": sample_config["api_key"]}
    assert client.config.timeout == int(sample_config["timeout"])
    assert client._simulate


def test_invalid_immich_config_type():
    with pytest.raises(ValidationError):
        ImmichClient([])  # type: ignore


def test_empty_immich_config():
    with pytest.raises(ValueError):
        ImmichClient({})


def test_invalid_immich_simulate_type(sample_config):
    with pytest.raises(TypeError):
        ImmichClient(sample_config, [])  # type: ignore


def test_invalid_immich_url(sample_config):
    sample_config["url"] = 123
    with pytest.raises(ValidationError):
        ImmichClient(sample_config)


def test_empty_immich_url(sample_config):
    del sample_config["url"]
    with pytest.raises(ValidationError):
        ImmichClient(sample_config)


def test_immich_urls(sample_config):
    srv = "https://demo.immich.app"
    endpoint = HttpUrl(srv + "/api")
    sample_config["url"] = srv
    assert ImmichClient(sample_config, True).config.url == endpoint
    sample_config["url"] = srv + "/"
    assert ImmichClient(sample_config, True).config.url == endpoint
    sample_config["url"] = srv + "/api"
    assert ImmichClient(sample_config, True).config.url == endpoint
    sample_config["url"] = srv + "/api/"
    assert ImmichClient(sample_config, True).config.url == endpoint


def test_invalid_immich_key(sample_config):
    sample_config["api_key"] = []
    with pytest.raises(ValidationError):
        ImmichClient(sample_config)


def test_empty_immich_key(sample_config):
    sample_config["api_key"] = ""
    with pytest.raises(ValidationError):
        ImmichClient(sample_config)


def test_immich_timeout_str(sample_config):
    sample_config["timeout"] = "123"
    client = ImmichClient(sample_config)
    assert client.config.timeout == 123  # noqa: PLR2004


def test_immich_timeout_float(sample_config):
    sample_config["timeout"] = 2.34
    with pytest.raises(ValidationError):
        ImmichClient(sample_config)


def test_immich_timeout_negative(sample_config):
    sample_config["timeout"] = -5
    with pytest.raises(ValidationError):
        ImmichClient(sample_config)


def test_invalid_immich_timeout(sample_config):
    sample_config["timeout"] = "invalid"
    with pytest.raises(ValidationError):
        ImmichClient(sample_config)


@pytest.fixture
def mock_response(mocker):
    mock = MagicMock()
    mocker.patch("requests.sessions.Session.request", return_value=mock)
    return mock


def check_response(
    mock_response, caplog, call_count=1, contains=None, contains_not=None
):
    assert mock_response.raise_for_status.call_count == call_count
    if contains:
        for string in contains:
            assert string in caplog.text
    if contains_not:
        for string in contains_not:
            assert string not in caplog.text


def test_ping_simulate(sample_config, caplog):
    assert ImmichClient(sample_config, True).ping()
    assert "Simulating" in caplog.text
    assert "responded successfully" in caplog.text


def test_ping_success(mock_response, sample_config, caplog):
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"res": "pong"}
    assert ImmichClient(sample_config).ping()
    check_response(
        mock_response, caplog, call_count=1, contains=["responded successfully"]
    )


def test_ping_unexpected_response(mock_response, sample_config, caplog):
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"error": "Not Found"}
    assert not ImmichClient(sample_config).ping()
    check_response(
        mock_response, caplog, call_count=1, contains=["Unexpected server response"]
    )


def test_ping_failure(mock_response, sample_config, caplog):
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError
    with pytest.raises(requests.exceptions.HTTPError):
        assert not ImmichClient(sample_config).ping()
    check_response(mock_response, caplog, call_count=1, contains_not=["responded"])


def test_ping_invalid_json_decode(mock_response, sample_config, caplog):
    mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    with pytest.raises(ValueError):
        assert not ImmichClient(sample_config).ping()
    check_response(mock_response, caplog, call_count=1, contains_not=["responded"])


def test_ping_invalid_json_type(mock_response, sample_config, caplog):
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = []
    with pytest.raises(TypeError):
        assert not ImmichClient(sample_config).ping()
    check_response(mock_response, caplog, call_count=1, contains_not=["responded"])


def test_http_error_with_message(mock_response, sample_config, caplog):
    mock_response.json.return_value = {
        "message": "bad request",
        "errors": "description",
    }
    err = requests.exceptions.HTTPError()
    err.response = mock_response
    mock_response.raise_for_status.side_effect = err
    mock_response.status_code = 123
    with pytest.raises(requests.exceptions.HTTPError):
        ImmichClient(sample_config).ping()
    check_response(
        mock_response,
        caplog,
        contains=["HTTP 123 error", "error message", "bad request"],
    )


def test_http_error_without_message(mock_response, sample_config, caplog):
    mock_response.json.return_value = {"error": "bad"}
    err = requests.exceptions.HTTPError()
    err.response = mock_response
    mock_response.raise_for_status.side_effect = err
    mock_response.status_code = 123
    with pytest.raises(requests.exceptions.HTTPError):
        ImmichClient(sample_config).ping()
    check_response(mock_response, caplog, contains=["HTTP 123 error", "Response JSON"])


def test_http_error_invalid_json(mock_response, sample_config, caplog):
    mock_response.json.side_effect = json.JSONDecodeError("x", "doc", 0)
    mock_response.text = "not json"
    err = requests.exceptions.HTTPError()
    err.response = mock_response
    mock_response.raise_for_status.side_effect = err
    mock_response.status_code = 123
    with pytest.raises(requests.exceptions.HTTPError):
        ImmichClient(sample_config).ping()
    check_response(
        mock_response, caplog, contains=["HTTP 123 error", "Response content"]
    )


def test_request_exception(mock_response, sample_config, caplog):
    mock_response.raise_for_status.side_effect = requests.exceptions.ConnectionError()
    with pytest.raises(requests.exceptions.ConnectionError):
        ImmichClient(sample_config).ping()
    check_response(mock_response, caplog, contains=["Request error"])


@pytest.fixture
def sample_query():
    return Query(
        filter=Filter(
            conditions={
                "key": 1,
                "color": "red",
            }
        )
    )


@pytest.fixture
def sample_response():
    return AssetsResponse.model_validate(
        {
            "assets": {
                "items": [{"id": 1}],
                "nextPage": None,
            }
        }
    ).model_dump()


def test_single_query_simulate(caplog, sample_config, sample_query):
    resp = ImmichClient(sample_config, True)._run_query(sample_query)
    assert "Simulating" in caplog.text
    assert "0 items" in caplog.text
    assert "Executing" not in caplog.text
    assert dict(resp.assets) == {"items": [], "nextPage": None}


def test_single_query_success(
    mock_response, sample_config, sample_query, sample_response, caplog
):
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = sample_response
    resp = ImmichClient(sample_config)._run_query(sample_query)
    check_response(
        mock_response, caplog, call_count=1, contains=["Executing", "1 items"]
    )
    assert dict(resp.assets) == sample_response["assets"]


def test_single_query_no_assets(mock_response, sample_config, sample_query, caplog):
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {}
    with pytest.raises(TypeError):
        ImmichClient(sample_config)._run_query(sample_query)
    check_response(mock_response, caplog, call_count=1, contains=["Executing"])


def test_single_query_no_items(mock_response, sample_config, sample_query, caplog):
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"assets": {"items": 123}}
    with pytest.raises(TypeError):
        ImmichClient(sample_config)._run_query(sample_query)
    check_response(mock_response, caplog, call_count=1, contains=["Executing"])


@pytest.fixture
def sample_conditions():
    return [
        Query(filter=Filter(conditions={"a": 1, "b": 2})),
        Query(filter=Filter(conditions={"a": 1, "c": 3, "d": 4})),
    ]


def test_single_query_cache(sample_config, sample_conditions, caplog):
    client = ImmichClient(sample_config)
    client._cache = {(("a", 1), ("b", 2)): [Asset.model_validate({"id": 1})]}
    queries = client.search_metadata([sample_conditions[0]])
    assert "from cache" in caplog.text
    assert queries[0].assets == client._cache[(("a", 1), ("b", 2))]


def test_search_simulate(sample_config, sample_conditions, caplog):
    queries = ImmichClient(sample_config, True).search_metadata(sample_conditions)
    assert "2 Immich metadata search" in caplog.text
    assert "Simulating" in caplog.text
    assert queries[0].cache_key() == (("a", 1), ("b", 2))
    assert queries[0].assets == []
    assert queries[1].cache_key() == (("a", 1), ("c", 3), ("d", 4))
    assert queries[1].assets == []


def test_search_once(
    mock_response, sample_config, sample_conditions, sample_response, caplog
):
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = sample_response
    queries = ImmichClient(sample_config).search_metadata([sample_conditions[0]])
    check_response(
        mock_response,
        caplog,
        call_count=1,
        contains=[
            "Immich query",
            "1 items in query page 1",
            "total of 1 assets",
        ],
    )
    assert queries[0].filter.conditions == sample_conditions[0].filter.conditions
    assert queries[0].assets[0].response == sample_response["assets"]["items"][0]


def test_search_invalid_page(
    mock_response, sample_config, sample_conditions, sample_response, caplog
):
    mock_response.raise_for_status.return_value = None
    sample_response["assets"]["nextPage"] = "invalid"
    mock_response.json.return_value = sample_response
    with pytest.raises(ValueError):
        ImmichClient(sample_config).search_metadata([sample_conditions[0]])
    check_response(mock_response, caplog, call_count=1, contains=["Executing"])


def test_search_multipage(
    mock_response, sample_config, sample_conditions, sample_response, caplog
):
    mock_response.raise_for_status.return_value = [None, None]
    response = copy.deepcopy(sample_response)
    response["assets"]["nextPage"] = "2"
    assert response != sample_response
    mock_response.json.side_effect = [response, sample_response]
    queries = ImmichClient(sample_config).search_metadata([sample_conditions[0]])
    check_response(
        mock_response,
        caplog,
        call_count=2,
        contains=[
            "Immich query",
            "1 items in query page 1",
            "1 items in query page 2",
            "total of 2 assets",
        ],
    )
    item = sample_response["assets"]["items"][0]
    assets = [Asset(response=item), Asset(response=item)]
    assert queries[0].filter.conditions == sample_conditions[0].filter.conditions
    assert queries[0].assets == assets
