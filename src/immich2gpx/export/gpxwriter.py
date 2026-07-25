from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from immich2gpx import __version__
from immich2gpx.jobs.job import Job
from immich2gpx.models.query import Query

logger = logging.getLogger(__name__)


class GPXConfig(BaseModel):
    """Define configuration options for GPX export."""

    directory: Path = Path("gpx")
    description_keys: list[str] = Field(default_factory=list)
    model_config = ConfigDict(validate_default=True, extra="forbid")

    @field_validator("directory", mode="before")
    @classmethod
    def normalize_dir(cls, value: Any) -> Any:
        """Convert directory configuration values to Path objects."""
        if isinstance(value, str):
            value = Path(value)
        return value

    @field_validator("directory", mode="after")
    @classmethod
    def check_dir(cls, value: Path) -> Path:
        """Validate that the GPX export directory exists."""
        if not value.exists():
            raise FileNotFoundError(
                f"GPX export directory does not exist: {value.resolve()}"
            )
        if not value.is_dir():
            raise NotADirectoryError(
                f"GPX export path is not a directory: {value.resolve()}"
            )
        logger.info(f"GPX export directory: {value.resolve()}")
        return value

    @field_validator("description_keys", mode="before")
    @classmethod
    def normalize_keys(cls, value: Any) -> Any:
        """Normalize description key configuration to a list."""
        if value is None or value == {}:
            value = []
        if isinstance(value, str):
            value = [value]
        return value


class GPXWriter:
    """Generate GPX tracks from Immich metadata queries."""

    def __init__(self, config: GPXConfig | Mapping[str, Any] | None = None) -> None:
        """Initialize the GPX writer with its configuration."""
        logger.debug("Initializing GPX writer")
        self.config = (
            GPXConfig() if config is None else GPXConfig.model_validate(config)
        )
        logger.debug("Successfully parsed GPX configuration")

    def create(self, job_name: str, queries: list[Query]) -> None:
        """Generate and write a GPX file for the provided queries."""
        logger.debug(f"Generating GPX file for job '{job_name}'")
        if not isinstance(queries, Iterable) or not all(
            isinstance(query, Query) for query in queries
        ):
            raise TypeError("Query results must be a list of queries")
        Job.check_job_name(job_name)

        gpx = ET.Element(
            "gpx",
            version="1.1",
            creator=f"immich2gpx {__version__}",
            xmlns="http://www.topografix.com/GPX/1/1",
        )

        metadata = ET.SubElement(gpx, "metadata")
        ET.SubElement(metadata, "name").text = f"Job '{job_name}'"
        sub = ET.SubElement(metadata, "desc")
        sub.text = f"Tool information: immich2gpx {__version__}, https://github.com/Griffsano/immich2gpx"
        ET.SubElement(metadata, "time").text = datetime.now(timezone.utc).isoformat()

        trk = ET.SubElement(gpx, "trk")
        ET.SubElement(trk, "name").text = job_name

        written_in_file = 0
        for query in queries:
            query_str = str(query)
            logger.debug(f"Creating track segment for query: {query_str}")
            trkseg = ET.SubElement(trk, "trkseg")
            ET.SubElement(trkseg, "src").text = query_str

            written_in_query = 0
            query.sort_assets_by_timestamp()
            for asset in query.assets:
                lat = asset.extract_key("latitude")
                lon = asset.extract_key("longitude")
                if not isinstance(lat, (int, float)) or not isinstance(
                    lon, (int, float)
                ):
                    logger.warning(f"Skipping asset with invalid coordinates: {asset}")
                    continue
                time = asset.get_timestamp()
                if time is None:
                    logger.warning(f"Skipping asset with invalid timestamp: {asset}")
                    continue

                trkpt = ET.SubElement(trkseg, "trkpt", lat=str(lat), lon=str(lon))
                ET.SubElement(trkpt, "time").text = time.isoformat()
                ET.SubElement(trkpt, "desc").text = ", ".join(
                    f"{key}={asset.extract_key(key)}"
                    for key in self.config.description_keys
                )
                written_in_query += 1

            logger.debug(
                f"Written {written_in_query}/{len(query.assets)} track points for query"
            )
            written_in_file = written_in_file + written_in_query
        logger.debug(f"Written {len(queries)} track segments for track")
        path = self.config.directory / f"{job_name}.gpx"
        ET.indent(gpx, "  ")
        ET.ElementTree(gpx).write(path, encoding="utf-8")
        logger.info(f"GPX file with {written_in_file} track points written to {path}")
