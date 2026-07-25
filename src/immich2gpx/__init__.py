"""immich2gpx package.

Command-line tool that queries filtered media metadata from an Immich server
and exports EXIF location data to GPX files.
"""

from __future__ import annotations

import importlib.metadata


def _get_version() -> str:
    """Return installed package version."""
    try:
        return importlib.metadata.version("immich2gpx")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover
        return "0.0.0"


__version__: str = _get_version()

__all__ = ["__version__"]
