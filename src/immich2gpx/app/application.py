from __future__ import annotations

import logging
from pathlib import Path

from immich2gpx.analysis.analyzer import Analyzer
from immich2gpx.config.loader import ConfigLoader
from immich2gpx.export.gpxwriter import GPXWriter
from immich2gpx.immich.client import ImmichClient
from immich2gpx.jobs.container import Container

logger = logging.getLogger(__name__)


class Application:
    """Coordinate configuration loading and execution of Immich jobs."""

    def __init__(self, configuration_path: str, simulate: bool) -> None:
        """Initialize the application with a configuration file."""
        logger.debug(f"Initializing application with config: {configuration_path}")
        if not isinstance(simulate, bool):
            logger.error("Simulation flag must be Boolean; defaulting to simulation")
            simulate = True
        self._simulate = simulate
        if self._simulate:
            logger.info("Will simulate all Immich server queries")
        path = Path(configuration_path.strip("'").strip('"'))
        self.config = ConfigLoader.load(path)
        self._containers: dict[str, Container] = {}
        self._immich: ImmichClient | None = None
        self._analyzer: Analyzer | None = None
        self._gpx: GPXWriter | None = None

    def _get_immich(self) -> ImmichClient:
        """Return the Immich client instance, creating it if necessary."""
        if not self._immich:
            logger.debug("Creating Immich server client")
            if self.config.immich is None:
                raise ValueError("Empty immich server client configuration")
            self._immich = ImmichClient(self.config.immich, self._simulate)
        return self._immich

    def _get_analyzer(self) -> Analyzer:
        """Return the analyzer instance, creating it if necessary."""
        if not self._analyzer:
            logger.debug("Creating analyzer tool")
            self._analyzer = Analyzer(self.config.analysis)
        return self._analyzer

    def _get_gpx(self) -> GPXWriter:
        """Return the GPX writer instance, creating it if necessary."""
        if not self._gpx:
            logger.debug("Creating GPX writer")
            self._gpx = GPXWriter(self.config.gpx)
        return self._gpx

    def check_immich_connection(self) -> bool:
        """Verify connectivity to the configured Immich server."""
        logger.debug("Checking Immich server connection")
        return self._get_immich().ping()

    def load_job(self, job_name: str) -> None:
        """Load the specified job and its dependent sub-jobs."""
        logger.debug(f"Loading top-level job '{job_name}'")
        if self.config.jobs is None:
            raise ValueError("Empty job configuration")
        self._containers[job_name] = Container(self.config.jobs, job_name)

    def run_jobs(self, show: bool, group: bool) -> None:
        """Execute all jobs and optionally display or group results."""
        logger.debug("Executing job list")

        for container in self._containers.values():
            logger.info(f"Running job container '{container.name}'")
            for job in container.jobs.values():
                logger.info(f"Running job '{job.name}'")
                self._get_immich().search_metadata(job.queries)
                container.merge_sub_jobs(job.name)

                if show or group:
                    items = job.get_all_assets()
                    if show:
                        self._get_analyzer().show(items)
                    if group:
                        self._get_analyzer().group(items)

    def compare(self, baseline_name: str, compare_name: str) -> None:
        """Compare the assets produced by two jobs."""
        if (
            baseline_name not in self._containers
            or baseline_name not in self._containers[baseline_name].jobs
        ):
            raise ValueError(f"Top-level baseline job '{baseline_name}' not found")
        if (
            compare_name not in self._containers
            or compare_name not in self._containers[compare_name].jobs
        ):
            raise ValueError(f"Top-level compare job '{compare_name}' not found")
        logger.info(
            f"Comparing baseline job '{baseline_name}' with compare job '{compare_name}'"
        )
        self._get_analyzer().compare(
            self._containers[baseline_name].jobs[baseline_name].get_all_assets(),
            self._containers[compare_name].jobs[compare_name].get_all_assets(),
        )

    def export_gpx(self) -> None:
        """Export GPX tracks for all standalone jobs."""
        logger.debug("Exporting GPX files")
        for container in self._containers.values():
            for job in container.jobs.values():
                if job.standalone:
                    self._get_gpx().create(job.name, job.queries)
