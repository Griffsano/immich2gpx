import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Asset(BaseModel):
    """Represent a single Immich media asset and its metadata."""

    response: dict[str, Any] = Field(default_factory=dict)
    _timestamp: datetime | None = None

    def get_timestamp(self) -> datetime | None:
        """Return the parsed asset timestamp from metadata."""
        if self._timestamp is None:
            self._timestamp = self._parse_timestamp("dateTimeOriginal")
        return self._timestamp

    def _parse_timestamp(self, name: str) -> datetime | None:
        """Parse an ISO timestamp field from the asset metadata."""
        timestamp = self.extract_key(name)
        try:
            return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            logger.warning(f"Asset does not have a valid '{name}' timestamp")
            return None

    def extract_key(self, key: Any) -> Any:
        """Return a metadata value from the asset or its EXIF information."""
        exif = self.response.get("exifInfo", {})
        if key in self.response:
            return self.response[key]
        if key in exif:
            return exif[key]
        return None

    def __str__(self) -> str:
        """Return a readable representation of the asset."""
        return ", ".join(
            f"{key}={self.extract_key(key)}" for key in ["id", "originalFileName"]
        )
