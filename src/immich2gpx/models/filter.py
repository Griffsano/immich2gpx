from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from datetime import datetime
from itertools import product
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class Filter(BaseModel):
    """Represent a normalized metadata filter for an Immich query."""

    conditions: dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(extra="forbid")
    _formatted_conditions: dict[str, Any] | None = None

    @property
    def formatted_conditions(self) -> dict[str, Any]:
        """Return filter conditions formatted for API requests."""
        if self._formatted_conditions is None:
            self._sort_conditions()
            self._formatted_conditions = {}
            for key, value in self.conditions.items():
                if value is None or value == {}:
                    self._formatted_conditions[key] = None
                elif isinstance(value, bool):
                    self._formatted_conditions[key] = str(value).lower()
                elif isinstance(value, (int, float)):
                    self._formatted_conditions[key] = value
                elif isinstance(value, datetime):
                    self._formatted_conditions[key] = value.isoformat()
                elif isinstance(value, list):
                    self._formatted_conditions[key] = tuple(value)
                else:
                    self._formatted_conditions[key] = str(value)
        return self._formatted_conditions

    def _sort_conditions(self) -> None:
        """Sort filter conditions to ensure stable ordering."""
        self.conditions = dict(sorted(self.conditions.items()))
        self._formatted_conditions = None

    @staticmethod
    def parse_filter(filter: Mapping[str, Any]) -> list[Filter]:
        """Convert a filter configuration into normalized query filters."""
        if not isinstance(filter, Mapping):
            raise TypeError("Conditions filter configuration must be a mapping")
        if not all(isinstance(key, str) for key in filter):
            raise TypeError(
                "Expected mapping with string keys, but found keys of type: "
                f"{[type(key) for key in filter]}"
            )
        if not filter:
            logger.warning("No media file filter found")
            return []
        if len(filter) != 1 or (op := next(iter(filter)).upper()) not in {"AND", "OR"}:
            raise ValueError(
                "Top-level conditions filter can only contain one AND or OR condition"
            )
        logger.debug(
            "Converting media file filter to disjunctive normal form of OR conditions"
        )
        filters = Filter._normalize_conditions(next(iter(filter.values())), op == "OR")
        logger.debug(f"Parsed filter condition: {Filter._list_to_str(filters, ' OR ')}")
        return filters

    @staticmethod
    def _normalize_conditions(  # noqa: PLR0912
        filters: list[Mapping[str, Any]] | Mapping[str, Any],
        or_condition: bool,
    ) -> list[Filter]:
        """Normalize filter expressions into disjunctive normal form."""
        condition_str = "OR" if or_condition else "AND"
        logger.debug(f"Normalizing {condition_str} condition: {filters}")
        dnf_list: list[list[Filter]] = []

        if isinstance(filters, Mapping):
            dictionary: Mapping[str, Any] = filters
            for key, value in dictionary.items():
                if isinstance(key, str) and key.upper() == "OR":
                    dnf_list.append(Filter._normalize_conditions(value, True))
                elif isinstance(key, str) and key.upper() == "AND":
                    dnf_list.append(Filter._normalize_conditions(value, False))
                else:
                    dnf_list.append([Filter(conditions={key: value})])
        elif isinstance(filters, list):
            dnf_list = [
                Filter._normalize_conditions(filter, or_condition) for filter in filters
            ]
        else:
            raise TypeError(f"Job filter item must be a mapping or list: {filters}")

        merged: list[Filter] = []
        if len(dnf_list) == 1:
            merged = next(iter(dnf_list))
        else:
            if or_condition:
                for dnf in dnf_list:
                    merged.extend(dnf)
            else:
                for combination in product(*dnf_list):
                    merged.append(Filter._merge_and_conditions(combination))
            merged = Filter._merge_or_conditions(merged)
        logger.debug(
            f"Normalized {condition_str} condition: "
            f"{Filter._list_to_str([Filter._list_to_str(lst, ', ') for lst in dnf_list], ' / ')} -> "
            f"{Filter._list_to_str(merged, ' OR ' if or_condition else ' AND ')}"
        )
        for filter in merged:
            Filter.model_validate(filter)
            filter._sort_conditions()
        return merged

    @staticmethod
    def _merge_or_conditions(
        filters: Iterable[Filter],
    ) -> list[Filter]:
        """Merge OR conditions while removing duplicates or redundancies."""
        logger.debug(f"Merging OR conditions: {[str(filter) for filter in filters]}")
        merged: list[Filter] = []
        for filter in filters:
            for idx, existing in enumerate(merged):
                if existing.conditions.items() == filter.conditions.items():
                    logger.warning(
                        f"Removing duplicate OR condition: {filter.conditions}"
                    )
                    break
                if existing.conditions.items() <= filter.conditions.items():
                    logger.warning(
                        f"Removing conservative OR condition: {filter.conditions}"
                    )
                    break
                if filter.conditions.items() <= existing.conditions.items():
                    logger.warning(
                        f"Removing conservative OR condition: {existing.conditions}"
                    )
                    merged.pop(idx)
                    merged.append(filter)
                    break
            else:
                merged.append(filter)
        return merged

    @staticmethod
    def _merge_and_conditions(
        filters: Iterable[Filter],
    ) -> Filter:
        """Merge AND conditions and detect conflicting keys."""
        logger.debug(f"Merging AND conditions: {[str(filter) for filter in filters]}")
        merged = Filter()
        for filter in filters:
            for key, value in filter.conditions.items():
                if key in merged.conditions:
                    logger.warning(f"Duplicate key in AND condition ignored: {key}")
                    if merged.conditions[key] != value:
                        raise ValueError(
                            f"Conflicting AND conditions for key '{key}': "
                            f"{merged.conditions[key]} != {value}"
                        )
                else:
                    merged.conditions[key] = value
        return merged

    def __str__(self) -> str:
        """Return a readable representation of the filter expression."""
        return " AND ".join(
            f"'{key}' = '{value}'" for key, value in self.conditions.items()
        )

    @staticmethod
    def _list_to_str(filter_list: list[Any], decimator: str) -> str:
        """Return a readable representation of a list."""
        return f"{decimator}".join(str(filter) for filter in filter_list)
