import pytest
from pydantic import ValidationError

from immich2gpx.immich.responses import AssetsPage, AssetsResponse, PongResponse
from immich2gpx.models.asset import Asset


def test_pong_response_valid():
    data = {"res": "pong"}
    response = PongResponse.model_validate(data)
    assert response.res == "pong"


def test_pong_response_invalid_value():
    data = {"res": "unexpected"}
    with pytest.raises(ValidationError):
        PongResponse.model_validate(data)


def test_to_assets_creates_asset_objects():
    items = [{"id": 1}, {"id": 2}]
    page = AssetsPage(items=items)
    assets = [Asset(response={"id": 1}), Asset(response={"id": 2})]
    assert assets == page.to_assets()


def test_next_page_number_none_returns_none():
    page = AssetsPage(items=[], nextPage=None)
    assert page.next_page_number is None


def test_next_page_number_valid_string():
    page = AssetsPage(items=[], nextPage="5")
    assert page.next_page_number == 5  # noqa: PLR2004


def test_next_page_number_valid_int():
    page = AssetsPage(items=[], nextPage=5)
    assert page.next_page_number == 5  # noqa: PLR2004


def test_next_page_number_invalid_string_raises():
    page = AssetsPage(items=[], nextPage="abc")
    with pytest.raises(ValueError) as exc:
        _ = page.next_page_number
    assert "Invalid next page" in str(exc.value)


def test_assets_response_model_parsing():
    data = {
        "assets": {
            "items": [{"id": 1}],
            "nextPage": "2",
        }
    }
    response = AssetsResponse.model_validate(data)
    assert isinstance(response.assets, AssetsPage)
    assert response.assets.items == [{"id": 1}]
    assert response.assets.next_page_number == 2  # noqa: PLR2004


def test_assets_page_allows_extra_fields():
    page = AssetsPage(items=[], nextPage="1", unexpected="value")  # type: ignore
    assert page.unexpected == "value"  # type: ignore
    assert page.model_extra["unexpected"] == "value"  # type: ignore


def test_assets_response_allows_extra_fields():
    data = {
        "assets": {
            "items": [],
            "nextPage": "1",
            "extra_field": 123,
        },
        "top_level_extra": "hello",
    }
    response = AssetsResponse.model_validate(data)
    assert response.model_extra["top_level_extra"] == "hello"  # type: ignore
    assert response.assets.model_extra["extra_field"] == 123  # type: ignore # noqa: PLR2004
