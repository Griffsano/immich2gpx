"""Tests for the command-line interface."""

from __future__ import annotations

import argparse
import runpy
import sys
from pathlib import Path

import pytest

from immich2gpx import _get_version
from immich2gpx.cli.cli import build_parser


def test_get_version():
    version = _get_version()
    assert isinstance(version, str)
    assert version != ""
    assert version != "0.0.0"


def parse_args(*args: str) -> argparse.Namespace:
    parser = build_parser()
    return parser.parse_args(list(args))


def test_help_argument() -> None:
    with pytest.raises(SystemExit) as exception_info:
        parse_args("--help")
    assert exception_info.value.code == 0


def test_version_argument() -> None:
    with pytest.raises(SystemExit) as exception_info:
        parse_args("--version")
    assert exception_info.value.code == 0


def test_default_arguments() -> None:
    args = parse_args()
    assert args.config == "immich2gpx.yaml"
    assert args.check_connection is False
    assert args.job is None
    assert args.gpx is False
    assert args.show is False
    assert args.group is False
    assert args.compare_with is None
    assert args.simulate is False
    assert args.logging_level == "INFO"


def test_config_argument() -> None:
    args = parse_args("--config", "folder/custom.yaml")
    assert args.config == "folder/custom.yaml"


def test_check_connection_flag() -> None:
    args = parse_args("--check-connection")
    assert args.check_connection is True


def test_job_argument() -> None:
    args = parse_args("--job", "main")
    assert args.job == "main"


def test_gpx_flag() -> None:
    args = parse_args("--job", "main", "--gpx")
    assert args.gpx is True


def test_show_flag() -> None:
    args = parse_args("--job", "main", "--show")
    assert args.show is True


def test_group_flag() -> None:
    args = parse_args("--job", "main", "--group")
    assert args.group is True


def test_compare_with_argument() -> None:
    args = parse_args("--job", "job1", "--compare-with", "job2")
    assert args.compare_with == "job2"


def test_simulate_flag() -> None:
    args = parse_args("--simulate")
    assert args.simulate is True


def test_logging_level_argument() -> None:
    args = parse_args("--logging-level", "DEBUG")
    assert args.logging_level == "DEBUG"


def test_invalid_logging_level() -> None:
    with pytest.raises(SystemExit) as exception_info:
        parse_args("--logging-level=INVALID")
    assert exception_info.value.code == 2  # noqa: PLR2004


def run_module(monkeypatch, arguments: list[str], expected_code):
    arguments.insert(0, "immich2gpx")
    monkeypatch.setattr(sys, "argv", arguments)
    with pytest.raises(SystemExit) as exception_info:
        runpy.run_module("immich2gpx.__main__", run_name="__main__")
    assert exception_info.value.code == expected_code


@pytest.fixture
def sample_config(tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config = [
        "immich:",
        "  url: https://demo.immich.app",
        "  api_key: apiKey",
        "analysis:",
        "  show_keys: id",
        "jobs:",
        "  main:",
        "  sub:",
    ]
    config_file.write_text("\n".join(config))
    return str(config_file)


def test_run_default(monkeypatch, capsys):
    run_module(monkeypatch, [], 0)
    captured = capsys.readouterr()
    assert "usage" in captured.out
    assert "options" in captured.out


def test_run_config(monkeypatch, sample_config, capsys):
    run_module(monkeypatch, [f"--config={sample_config}"], 0)
    captured = capsys.readouterr()
    assert sample_config in captured.err


def test_run_connection(monkeypatch, sample_config, capsys):
    run_module(
        monkeypatch,
        [f"--config='{sample_config}'", "--check-connection", "--simulate"],
        0,
    )
    captured = capsys.readouterr()
    assert "responded successfully" in captured.err


def test_run_no_job(monkeypatch, sample_config, capsys):
    run_module(monkeypatch, [f"--config='{sample_config}'", "--show"], 2)
    captured = capsys.readouterr()
    assert "Missing required --job argument" in captured.err


def test_run_run_job(monkeypatch, sample_config, capsys):
    run_module(monkeypatch, [f"--config='{sample_config}'", "--job=main"], 0)
    captured = capsys.readouterr()
    assert "job 'main'" in captured.err


def test_run_compare_job(monkeypatch, sample_config, capsys):
    run_module(
        monkeypatch,
        [f"--config='{sample_config}'", "--job=main", "--compare-with=sub"],
        0,
    )
    captured = capsys.readouterr()
    assert "job 'main'" in captured.err
    assert "job 'sub'" in captured.err
    assert "baseline job 'main'" in captured.err
    assert "compare job 'sub'" in captured.err


def test_export(monkeypatch, sample_config, capsys):
    run_module(monkeypatch, [f"--config='{sample_config}'", "--job=main", "--gpx"], 0)
    captured = capsys.readouterr()
    assert "track points written" in captured.err
