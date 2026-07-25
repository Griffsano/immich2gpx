"""Command-line interface handling."""

from __future__ import annotations

import argparse
import logging
import sys

from immich2gpx import __version__
from immich2gpx.app.application import Application
from immich2gpx.utils.logging import configure_logging

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Create and configure the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="immich2gpx",
        description=(
            "Command-line tool that queries filtered media metadata from an Immich "
            "server and exports EXIF location data to GPX files"
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="immich2gpx.yaml",
        help="Path to the YAML config file. Defaults to immich2gpx.yaml.",
    )
    parser.add_argument(
        "--check-connection",
        action="store_true",
        help="Check connection to the Immich server.",
    )
    parser.add_argument(
        "--job",
        type=str,
        help="Defines the job to be run. Also executes sub-jobs.",
    )
    parser.add_argument(
        "--gpx",
        action="store_true",
        help="Write the parsed EXIF location data to GPX files.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Execute the queries and print the resulting metadata.",
    )
    parser.add_argument(
        "--group",
        action="store_true",
        help="Execute the queries, group the media files, and print the metadata.",
    )
    parser.add_argument(
        "--compare-with",
        type=str,
        help="Compare a job with the job specified by --job.",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Output the Immich requests for analysis but do not execute them.",
    )
    parser.add_argument(
        "--logging-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Define the logging level (DEBUG, INFO, WARNING, ERROR).",
    )

    return parser


def main() -> int:
    """Run the CLI entry point and execute the requested operations."""
    args = build_parser().parse_args(args=None if sys.argv[1:] else ["--help"])
    configure_logging(args.logging_level)

    application = Application(args.config, args.simulate)

    if args.check_connection:
        application.check_immich_connection()

    if not args.job and (args.show or args.group or args.gpx or args.compare_with):
        logger.error("Missing required --job argument for selected operation")
        return 2

    if args.job:
        application.load_job(args.job)

        if args.compare_with:
            application.load_job(args.compare_with)

        application.run_jobs(args.show, args.group)

        if args.compare_with:
            application.compare(args.job, args.compare_with)

        if args.gpx:
            application.export_gpx()

    return 0
