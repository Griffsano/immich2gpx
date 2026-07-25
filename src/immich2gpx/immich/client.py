from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Mapping
from typing import Any

import requests
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    ValidationError,
    field_validator,
)

from immich2gpx.immich.responses import AssetsResponse, PongResponse
from immich2gpx.models.asset import Asset
from immich2gpx.models.query import Query

logger = logging.getLogger(__name__)


class ImmichConfig(BaseModel):
    """Store configuration for connecting to the Immich API."""

    url: HttpUrl
    api_key: str
    timeout: int = Field(default=10, gt=0)
    model_config = ConfigDict(validate_default=True, extra="forbid")

    @field_validator("url", mode="after")
    @classmethod
    def normalize_url(cls, value: HttpUrl) -> HttpUrl:
        """Normalize the API base URL to include the /api path."""
        value_str = str(value).strip().rstrip("/").removesuffix("/api")
        return HttpUrl(value_str + "/api")

    @field_validator("api_key", mode="after")
    @classmethod
    def check_api_key(cls, value: str) -> str:
        """Validate that the Immich API key is not empty."""
        value = value.strip()
        if not value:
            raise ValueError("Immich API key must not be empty")
        return value

    @property
    def headers(self) -> dict[str, str]:
        """Return HTTP headers required for Immich API requests."""
        return {"x-api-key": self.api_key}


class ImmichClient:
    """Execute metadata searches against the Immich REST API."""

    def __init__(
        self,
        config: ImmichConfig | Mapping[str, Any],
        simulate: bool = False,
    ) -> None:
        """Initialize the Immich API client with its configuration."""
        logger.debug("Initializing Immich client")
        self.config = ImmichConfig.model_validate(config)

        if not isinstance(simulate, bool):
            raise TypeError("Immich simulation flag must be a Boolean value")
        self._simulate = simulate

        self._cache: dict[tuple[tuple[str, Any], ...], list[Asset]] = {}

        self._session = requests.Session()
        self._session.headers.update(self.config.headers)
        logger.debug("Successfully parsed Immich client configuration")

    def ping(self) -> bool:
        """Check whether the Immich server is reachable."""
        url = f"{self.config.url}/server/ping"
        query_str = f"GET {url}"

        if self._simulate:
            logger.info(f"Simulating Immich server ping: {query_str}")
            result = {"res": "pong"}
        else:
            logger.debug(f"Executing Immich server ping: {query_str}")
            response = self._session.get(url, timeout=self.config.timeout)
            result = self._handle_response(response)

        try:
            PongResponse.model_validate(result)
            logger.info("Immich server responded successfully")
            return True
        except ValidationError:
            logger.warning(f"Unexpected server response: {result}")
            return False

    def search_metadata(self, queries: Iterable[Query]) -> list[Query]:
        """Execute metadata searches for the provided queries."""
        queries = list(queries)
        logger.info(f"Executing {len(queries)} Immich metadata searches")

        total_assets = 0
        for query in queries:
            cache_key = query.cache_key()
            logger.debug(f"Starting Immich metadata search: {query!s}")
            assets: list[Asset] = []

            if cache_key in self._cache:
                logger.info("Loading query results from cache")
                assets = self._cache[cache_key].copy()
            else:
                page: int | None = 1
                while page:
                    data = self._run_query(query, page)
                    assets.extend(data.assets.to_assets())
                    page = data.assets.next_page_number
                self._cache[cache_key] = assets

            query.assets = assets
            total_assets += len(assets)
            logger.debug(f"Query returned {len(assets)} assets")

        logger.info(f"Metadata searches resulted in a total of {total_assets} assets")
        return queries

    def _run_query(self, query: Query, page: int = 1) -> AssetsResponse:
        """Execute a single paginated metadata search request."""
        payload = query.payload(page)
        url = f"{self.config.url}/search/metadata"
        query_str = f"POST {url}: {payload}"

        if self._simulate:
            logger.info(f"Simulating Immich query: {query_str}")
            result: dict[str, Any] = {"assets": {"items": [], "nextPage": None}}
        else:
            logger.debug(f"Executing Immich query: {query_str}")
            response = self._session.post(
                url,
                json=payload,
                timeout=self.config.timeout,
            )
            result = self._handle_response(response)

        try:
            parsed = AssetsResponse.model_validate(result)
        except ValidationError as error:
            raise TypeError("Received invalid API response structure") from error

        logger.debug(f"Received {len(parsed.assets.items)} items in query page {page}")
        return parsed

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        """Validate and decode a JSON response from the server."""
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            resp = err.response
            if resp is not None:
                logger.error(f"HTTP {resp.status_code} error during request: {err}")
                try:
                    data = resp.json()
                except json.JSONDecodeError:
                    logger.error(f"Response content not JSON: {resp.text}")
                else:
                    if isinstance(data, dict) and "message" in data:
                        logger.error(f"Server error message: {data['message']}")
                    else:
                        logger.error(f"Response JSON: {data}")
            raise
        except requests.exceptions.RequestException as err:
            logger.error(f"Request error: {err}")
            raise

        try:
            result = response.json()
        except json.JSONDecodeError as error:
            raise ValueError("Server returned invalid JSON response") from error

        if not isinstance(result, dict):
            raise TypeError(f"JSON response is not a dict: {result}")
        return result
