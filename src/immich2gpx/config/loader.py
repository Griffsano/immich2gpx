from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import BaseModel, ConfigDict
from yaml.nodes import ScalarNode

from immich2gpx.analysis.analyzer import AnalyzerConfig
from immich2gpx.export.gpxwriter import GPXConfig
from immich2gpx.immich.client import ImmichConfig
from immich2gpx.jobs.job import JobConfig

logger = logging.getLogger(__name__)


class AppConfig(BaseModel):
    """Define the top-level application configuration schema."""

    immich: ImmichConfig | None = None
    analysis: AnalyzerConfig | None = None
    gpx: GPXConfig | None = None
    references: Mapping[str, Any] | list[Mapping[str, Any]] | None = None
    jobs: Mapping[str, JobConfig] | list[Mapping[str, JobConfig]] | None = None
    model_config = ConfigDict(validate_default=True, extra="forbid")


class ConfigLoader:
    """Load YAML configuration files with include and reference support."""

    @classmethod
    def load(cls, path: Path) -> AppConfig:
        """Load, resolve, and validate the application configuration."""
        logger.info(f"Loading configuration from: {path}")
        data = cls._load_yaml(path)
        resolved = cls._resolve(data)
        return AppConfig.model_validate(resolved)

    @classmethod
    def _load_yaml(cls, path: Path) -> dict[str, Any]:
        """Parse a YAML file and process custom include directives."""
        logger.debug(f"Parsing YAML configuration: {path.absolute()}")
        if not path.exists():
            raise FileNotFoundError(f"Config file does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"Path is not a config file: {path}")

        class Loader(yaml.SafeLoader):
            pass

        def include(loader: Loader, node: ScalarNode) -> dict[str, Any]:
            include_target = loader.construct_scalar(node)
            include_path = (path.parent / include_target).resolve()
            if not str(include_path).startswith(str(path.parent.resolve())):
                raise ValueError(
                    f"Include directory outside config path: {include_target}"
                )
            return cls._load_yaml(include_path)

        Loader.add_constructor("!include", include)

        with path.open("r", encoding="utf-8") as fh:
            return cast("dict[str, Any]", Loader(fh).get_single_data())

    @classmethod
    def _resolve(cls, config: Mapping[str, Any]) -> dict[str, Any]:
        """Resolve reference definitions within the configuration."""
        resolved = cls._resolve_node(config, {}, set())
        if not isinstance(resolved, dict):
            raise TypeError(f"Expected dict[str, Any], but got {type(resolved)}")
        if not all(isinstance(k, str) for k in resolved):
            raise TypeError(
                f"Expected dict with string keys, but found keys of type: {[type(k) for k in resolved]}"
            )
        if resolved == {}:
            logger.warning("Resolved configuration is empty")
        return resolved

    @classmethod
    def _resolve_node(
        cls,
        node: Any,
        references: Mapping[str, Any],
        visited: set[str],
    ) -> Any:
        """Recursively resolve references in a configuration node."""
        loc_ref = dict(references)
        loc_vis = visited.copy()

        if isinstance(node, dict):
            if "references" in node:
                new_ref = node["references"]
                if isinstance(new_ref, list):
                    merged: dict[str, Any] = {}
                    for dictionary in new_ref:
                        if dictionary is None:
                            continue
                        cls._check_duplicates(merged, dictionary)
                        merged.update(dictionary)
                    new_ref = merged
                if new_ref is not None:
                    cls._check_duplicates(loc_ref, new_ref)
                    logger.debug(f"Adding reference definitions: {new_ref.keys()}")
                    loc_ref.update(new_ref)
            if "ref" in node:
                return cls._resolve_ref(node["ref"], loc_ref, loc_vis)
            return {k: cls._resolve_node(v, loc_ref, loc_vis) for k, v in node.items()}

        if isinstance(node, list):
            return [cls._resolve_node(i, loc_ref, loc_vis) for i in node]

        if node is None:
            return {}

        return node

    @classmethod
    def _resolve_ref(
        cls, name: str, references: Mapping[str, Any], visited: set[str]
    ) -> Any:
        """Resolve a named reference from the configuration."""
        logger.debug(f"Resolving reference: {name}")
        if name in visited:
            raise RecursionError(f"Circular reference detected: {name}")
        visited.add(name)

        if name not in references:
            raise KeyError(f"Unknown reference: {name}")
        return cls._resolve_node(references[name], references, visited)

    @staticmethod
    def _check_duplicates(dict1: Mapping[str, Any], dict2: Mapping[str, Any]) -> None:
        """Raise error if inputs are not mappings or have duplicate keys."""
        if not isinstance(dict1, Mapping) or not isinstance(dict2, Mapping):
            raise TypeError(f"Reference definition is not a mapping: {dict1} / {dict2}")
        if not dict1.keys().isdisjoint(dict2):
            duplicates = dict1.keys() & dict2.keys()
            raise ValueError(f"Duplicate reference definition: {', '.join(duplicates)}")
