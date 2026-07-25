from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from immich2gpx.models.asset import Asset
from immich2gpx.models.filter import Filter

logger = logging.getLogger(__name__)


class Query:
    """Represent a metadata query and its associated results."""

    filter: Filter
    assets: list[Asset]

    def __init__(
        self,
        filter: Filter | None = None,
        assets: list[Asset] | Asset | None = None,
    ) -> None:
        """Initialize a query with optional filter and assets."""
        self.filter = Filter() if filter is None else filter
        if not isinstance(self.filter, Filter):
            raise TypeError("Filter for query must be a Filter")
        if assets is None:
            self.assets = []
        elif isinstance(assets, Asset):
            self.assets = [assets]
        else:
            self.assets = assets
        if not isinstance(self.assets, list) or not all(
            isinstance(asset, Asset) for asset in self.assets
        ):
            raise TypeError("Assets for query must be a list of Assets")

    @staticmethod
    def from_conditions(filter: Mapping[str, Any]) -> list[Query]:
        """Create queries from normalized filter conditions."""
        filters = Filter.parse_filter(filter)
        return [Query(filter=filter) for filter in filters]

    def cache_key(self) -> tuple[tuple[str, Any], ...]:
        """Return a stable cache key for the query filter."""
        return tuple(self.filter.formatted_conditions.items())

    def compare_cache_key(self, query: Query) -> bool:
        """Check whether another query has the same cache key."""
        return self.cache_key() == query.cache_key()

    def payload(self, page: int) -> dict[str, Any]:
        """Construct the API payload for a metadata search."""
        payload = self.filter.formatted_conditions.copy()
        payload.setdefault("order", "desc")
        payload.setdefault("size", 250)
        payload["page"] = page
        payload["withExif"] = True
        payload["withPeople"] = True
        return payload

    def sort_assets_by_timestamp(self) -> None:
        """Sort assets by their parsed timestamp."""

        def key(asset: Asset) -> tuple[bool, datetime | None]:
            ts = asset.get_timestamp()
            return (ts is not None, ts)

        self.assets.sort(key=key)

    def __str__(self) -> str:
        """Return a readable representation of the query filter."""
        return str(self.filter) if self.filter else ""
