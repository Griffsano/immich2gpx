from __future__ import annotations

import fnmatch
import logging
from collections.abc import Mapping
from typing import Any

from immich2gpx.jobs.job import Job, JobConfig

logger = logging.getLogger(__name__)


class Container:
    """Manage job dependency traversal and orchestration."""

    def __init__(
        self,
        config: Mapping[str, JobConfig]
        | list[Mapping[str, JobConfig]]
        | Mapping[str, Any]
        | list[Mapping[str, Any]],
        job_name: str,
    ) -> None:
        """Initialize a container for the specified top-level job."""
        logger.debug(f"Initializing job container for main job '{job_name}'")
        if job_name == "":
            raise ValueError("Job name must not be empty")
        self.name: str = job_name
        self.config: dict[str, JobConfig] = {}
        if isinstance(config, Mapping):
            self.config = dict(config)
        elif isinstance(config, list):
            for job in config:
                self.config.update(job)
        else:
            raise TypeError("Job configuration must be a mapping or list of mappings")
        if not self.config:
            raise ValueError("Jobs not configured")
        self.jobs: dict[str, Job] = {}
        self._create_job_list(job_name, set(), True)
        logger.debug(f"Order of jobs: {', '.join(list(self.jobs))}")

    def _create_job_list(
        self, job_name: str, recursion_stack: set[str], standalone_job: bool
    ) -> None:
        """Traverse job dependencies with depth-first search and construct job list."""
        logger.debug(f"Traversing to job '{job_name}'")

        if job_name in recursion_stack:
            raise RecursionError(f"Circular dependency detected for job '{job_name}'")
        if job_name in self.jobs:
            if standalone_job:
                self.jobs[job_name].standalone = standalone_job
            return

        recursion_stack.add(job_name)
        job = Job(self.config.get(job_name, {}), job_name)
        job.standalone = standalone_job

        for sub_expr in job.config.merge_jobs:
            matching_list = self._match_job_names(sub_expr)
            job.merge_job_names.extend(matching_list)
            for matching in matching_list:
                self._create_job_list(matching, recursion_stack, False)

        for sub_expr in job.config.run_jobs:
            matching_list = self._match_job_names(sub_expr)
            job.run_job_names.extend(matching_list)
            for matching in matching_list:
                self._create_job_list(matching, recursion_stack, True)

        self.jobs[job_name] = job
        recursion_stack.remove(job_name)

    def _match_job_names(self, expression: str) -> list[str]:
        """Return job names matching a wildcard expression."""
        all_jobs = self.config.keys()
        return [j for j in all_jobs if fnmatch.fnmatch(j, expression)]

    def merge_sub_jobs(self, job_name: str) -> None:
        """Merge queries from configured sub-jobs into the target job."""
        job = self.jobs.get(job_name)
        if not job:
            raise ValueError(f"Job '{job_name}' not found")
        for sub_name in job.merge_job_names:
            logger.info(f"Merging job '{sub_name}' into '{job.name}'")
            sub = self.jobs.get(sub_name)
            if sub is None:
                raise ValueError(f"Merge job '{sub_name}' not found")
            job.merge_queries(sub)
