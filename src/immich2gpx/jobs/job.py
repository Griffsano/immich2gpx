from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from itertools import chain
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from immich2gpx.models.asset import Asset
from immich2gpx.models.query import Query

logger = logging.getLogger(__name__)


class JobConfig(BaseModel):
    """Define configuration for a single processing job."""

    merge_jobs: list[str] = Field(default_factory=list)
    run_jobs: list[str] = Field(default_factory=list)
    filter: Mapping[str, Any] = Field(default_factory=dict)
    references: Mapping[str, Any] | None = None
    model_config = ConfigDict(validate_default=True, extra="forbid")

    @field_validator("merge_jobs", "run_jobs", mode="before")
    @classmethod
    def normalize_keys(cls, value: Any) -> Any:
        """Normalize job name configuration values to lists."""
        if value is None or value == {}:
            value = []
        if isinstance(value, str):
            value = [value]
        return value


class Job:
    """Represent a configured job that executes metadata queries."""

    def __init__(self, config: JobConfig | Mapping[str, Any], job_name: str) -> None:
        """Initialize a job with its configuration."""
        logger.debug(f"Initializing job '{job_name}'")
        self.check_job_name(job_name)
        self.name = job_name
        if config == {}:
            logger.warning(f"Job '{job_name}' not configured")
        self.config = JobConfig.model_validate(config)
        self.merge_job_names: list[str] = []
        self.run_job_names: list[str] = []
        self.standalone: bool | None = None
        self.queries = Query.from_conditions(self.config.filter)
        logger.debug(f"Successfully parsed configuration for job '{self.name}'")

    def merge_queries(self, job: Job) -> None:
        """Merge queries from another job without duplicates."""
        for new in job.queries:
            for query in self.queries:
                if query.compare_cache_key(new):
                    break
            else:
                self.queries.append(new)

    def get_all_assets(self) -> list[Asset]:
        """Return all assets collected by the job queries."""
        return list(chain.from_iterable(q.assets for q in self.queries))

    @staticmethod
    def check_job_name(job_name: str) -> bool:
        """Validate that the job name contains only allowed characters."""
        if job_name == "":
            raise ValueError("Job name must not be empty")
        if re.compile(r"[^\w\-.]+").search(job_name):
            raise ValueError(f"Job name contains forbidden characters: {job_name}")
        return True
