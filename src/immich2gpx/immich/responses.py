from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from immich2gpx.models.asset import Asset


class PongResponse(BaseModel):
    """Model the response from the Immich ping endpoint."""

    res: Literal["pong"]
    model_config = ConfigDict(extra="allow")


class AssetsPage(BaseModel):
    """Represent a paginated list of asset metadata items."""

    items: list[dict[Any, Any]]
    nextPage: str | int | None = None
    model_config = ConfigDict(extra="allow")

    def to_assets(self) -> list[Asset]:
        """Convert raw asset dictionaries into Asset objects."""
        return [Asset(response=item) for item in self.items]

    @property
    def next_page_number(self) -> int | None:
        """Return the next page number if pagination continues."""
        next_page = self.nextPage
        try:
            if next_page is None:
                return None
            return int(next_page)
        except ValueError as error:
            raise ValueError(
                f"Invalid next page: {next_page} with type {type(next_page)}"
            ) from error


class AssetsResponse(BaseModel):
    """Model the response structure for metadata search results."""

    assets: AssetsPage
    model_config = ConfigDict(extra="allow")
