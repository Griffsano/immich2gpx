from pathlib import Path

import pytest

from immich2gpx.app.application import Application

SIMULATE = True
CONFIG_LIST = [
    "config/example_quickstart.yaml",
    "config/example_include.yaml",
    "config/example_references.yaml",
    "config/example_schema.yaml",
]

pytestmark = pytest.mark.parametrize("config_path", CONFIG_LIST)


def convert_list(possible_list):
    if isinstance(possible_list, list):
        return possible_list
    if isinstance(possible_list, dict):
        return list(possible_list.keys())
    else:
        return [possible_list]


def convert_dict(possible_dict):
    if isinstance(possible_dict, dict):
        return possible_dict
    if isinstance(possible_dict, list):
        items = {}
        for item in possible_dict:
            items.update(item)
        return items
    else:
        raise NotImplementedError


def test_example_config(config_path):
    Application(config_path, True)


def test_example_immich(config_path):
    app = Application(config_path, SIMULATE)
    immich = app._get_immich()
    settings = app.config.immich
    assert settings
    assert immich.config.url == settings.url
    assert immich.config.headers == {"x-api-key": settings.api_key}
    assert immich.config.timeout == settings.timeout
    assert immich.ping()


def test_example_analyzer(config_path):
    app = Application(config_path, SIMULATE)
    analyzer = app._get_analyzer()
    settings = app.config.analysis
    if settings:
        assert analyzer.config.show_keys == convert_list(settings.show_keys)
        assert analyzer.config.group_by_keys == convert_list(settings.group_by_keys)
    else:
        assert analyzer.config.show_keys == []
        assert analyzer.config.group_by_keys == []


def test_example_jobs(config_path):
    app = Application(config_path, SIMULATE)
    jobs = convert_dict(app.config.jobs)
    for job_name in jobs:
        app.load_job(job_name)
        job = app._containers[job_name].jobs[job_name]
        settings = jobs[job_name]
        if settings.merge_jobs:
            assert job.config.merge_jobs == convert_list(settings.merge_jobs)
        if settings.run_jobs:
            assert job.config.run_jobs == convert_list(settings.run_jobs)
    app.run_jobs(True, True)


def test_example_gpx(config_path):
    app = Application(config_path, SIMULATE)
    gpx = app._get_gpx()
    settings = app.config.gpx
    if settings:
        assert gpx.config.directory == Path(settings.directory)
        assert gpx.config.description_keys == convert_list(settings.description_keys)
    else:
        assert gpx.config.directory == Path("gpx")
        assert gpx.config.description_keys == []
    jobs = convert_dict(app.config.jobs)
    for job_name in jobs:
        app.load_job(job_name)
    app.run_jobs(True, True)
    app.export_gpx()
