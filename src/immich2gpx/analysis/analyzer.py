from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator
from tabulate import tabulate

from immich2gpx.models.asset import Asset

logger = logging.getLogger(__name__)


class AnalyzerConfig(BaseModel):
    """Define configuration for asset analysis operations."""

    show_keys: list[str] = Field(default_factory=list)
    group_by_keys: list[str] = Field(default_factory=list)
    model_config = ConfigDict(validate_default=True, extra="forbid")

    @field_validator("show_keys", "group_by_keys", mode="before")
    @classmethod
    def normalize_keys(cls, value: Any, info: ValidationInfo) -> Any:
        """Normalize analyzer configuration keys to lists."""
        if value is None or value == {}:
            value = []
        if isinstance(value, str):
            value = [value]
        return value


class Analyzer:
    """Analyze Immich assets by displaying, grouping, or comparing metadata."""

    def __init__(
        self, config: AnalyzerConfig | Mapping[str, Any] | None = None
    ) -> None:
        """Initialize the analyzer with its configuration."""
        logger.debug("Initializing Analyzer")
        self.config = (
            AnalyzerConfig()
            if config is None
            else AnalyzerConfig.model_validate(config)
        )
        logger.debug("Analyzer configuration loaded successfully")

    def show(self, assets: Iterable[Asset]) -> list[dict[str, Any]]:
        """Display selected metadata fields for each asset."""
        result: list[dict[str, Any]] = []

        assets_len = len(list(assets))
        logger.info(f"Showing {assets_len} assets")

        if self.config.show_keys == []:
            logger.warning(
                "Showing no assets because configuration 'show_keys' is empty"
            )
        elif assets_len > 0:
            result = [
                {key: asset.extract_key(key) for key in self.config.show_keys}
                for asset in assets
            ]
            for line in tabulate(
                result,
                headers="keys",
                headersglobalalign="center",
                tablefmt="simple",
            ).splitlines():
                logger.info(line)

        return result

    def group(
        self, assets: Iterable[Asset]
    ) -> dict[tuple[tuple[str, Any], ...], list[Asset]]:
        """Group assets by configured metadata keys."""
        groups: dict[tuple[tuple[str, Any], ...], list[Asset]] = defaultdict(list)

        if self.config.group_by_keys == []:
            logger.warning(
                "Showing no groups because configuration 'group_by_keys' is empty"
            )
        else:
            for asset in assets:
                key_tuple = tuple(
                    (key, asset.extract_key(key)) for key in self.config.group_by_keys
                )
                groups[key_tuple].append(asset)

            for key_tuple, grouped_assets in groups.items():
                key_str = ", ".join(
                    [f"'{key}' = '{value}'" for key, value in key_tuple]
                )
                logger.info(f"Group {key_str}: {len(grouped_assets)} assets")
                self.show(grouped_assets)

        return groups

    def compare(
        self, baseline: Iterable[Asset], compare: Iterable[Asset]
    ) -> dict[str, set[str]]:
        """Compare two asset collections and report differences."""
        logger.debug("Starting comparison of baseline and compare assets")

        baseline_assets = [a for a in baseline if a.extract_key("id") is not None]
        compare_assets = [a for a in compare if a.extract_key("id") is not None]

        skipped_baseline = len(list(baseline)) - len(baseline_assets)
        skipped_compare = len(list(compare)) - len(compare_assets)

        if skipped_baseline:
            logger.warning(f"Skipped {skipped_baseline} baseline assets without ID")
        if skipped_compare:
            logger.warning(f"Skipped {skipped_compare} compare assets without ID")

        baseline_ids = {asset.extract_key("id") for asset in baseline_assets}
        compare_ids = {asset.extract_key("id") for asset in compare_assets}

        only_baseline = baseline_ids - compare_ids
        only_compare = compare_ids - baseline_ids
        both = baseline_ids & compare_ids

        logger.info(f"{len(only_baseline)} assets present only in baseline")
        self.show([a for a in baseline_assets if a.extract_key("id") in only_baseline])

        logger.info(f"{len(only_compare)} assets present only in compare")
        self.show([a for a in compare_assets if a.extract_key("id") in only_compare])

        logger.info(f"{len(both)} assets present in both sets")
        self.show([a for a in baseline_assets if a.extract_key("id") in both])

        return {
            "only_baseline": only_baseline,
            "only_compare": only_compare,
            "both": both,
        }
