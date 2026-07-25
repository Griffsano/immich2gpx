from pathlib import Path

import pytest
from pydantic import HttpUrl

from immich2gpx.app.application import Application
from immich2gpx.models.asset import Asset


@pytest.fixture
def sample_config(tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    gpx_directory = tmp_path / "outputFolder"
    gpx_directory.mkdir()
    config = [
        "immich:",
        "  url: https://demo.immich.app",
        "  api_key: apiKey",
        "analysis:",
        "  show_keys:",
        "    - id",
        "    - file",
        "  group_by_keys: file",
        "jobs:",
        "  main:",
        "    merge_jobs: sub",
        "  sub:",
        "    filter:",
        "      and:",
        "        color: red",
        "  empty:",
        "gpx:",
        f"  directory: {gpx_directory}",
    ]
    config_file.write_text("\n".join(config))
    return str(config_file), gpx_directory


def test_empty_application_config(sample_config):
    config_file = Path(sample_config[0])
    config_file.write_text("")
    Application(str(config_file), True)


def test_application_config(sample_config):
    Application(sample_config[0], True)


def test_application_config_quotes(sample_config):
    path = f"'{sample_config[0]}'"
    Application(path, True)


def test_invalid_application_sim_flag(sample_config):
    app = Application(sample_config[0], "yes")  # type: ignore
    assert app._simulate


def test_application_no_simulate(sample_config):
    app = Application(sample_config[0], False)
    assert not app._get_immich()._simulate


def test_application_getters(sample_config):
    app = Application(sample_config[0], True)
    assert app._get_immich().config.url == HttpUrl("https://demo.immich.app/api")
    assert app._get_immich()._simulate
    assert app._get_analyzer().config.show_keys == ["id", "file"]
    assert app._get_gpx().config.directory == sample_config[1]


def test_application_empty_immich_config(sample_config):
    app = Application(sample_config[0], True)
    app.config.immich = None
    with pytest.raises(ValueError):
        app._get_immich()


def test_application_empty_job_config(sample_config):
    app = Application(sample_config[0], True)
    app.config.jobs = None
    with pytest.raises(ValueError):
        app.load_job("")


def test_application_immich_connection(sample_config):
    app = Application(sample_config[0], True)
    assert app.check_immich_connection()


def test_application_load_jobs(sample_config):
    app = Application(sample_config[0], True)
    app.load_job("main")
    cont = app._containers.get("main")
    assert cont
    assert "main" in cont.jobs
    assert "sub" in cont.jobs


def create_app_with_immich_cache(config_file: str):
    app = Application(config_file, True)
    app.load_job("main")
    items = [Asset(response={"id": 1234567890, "file": "test.jpg"})]
    app._get_immich()._cache[(("color", "red"),)] = items
    return app, [i.model_dump()["response"] for i in items]


def test_application_run_jobs(sample_config, caplog):
    app, items = create_app_with_immich_cache(sample_config[0])
    app.run_jobs(False, False)
    cont = app._containers.get("main")
    assert cont
    job = cont.jobs.get("main")
    assert job
    assert job.get_all_assets() == [Asset(response=i) for i in items]
    assert "'sub' into 'main'" in caplog.text


def test_application_silent(sample_config, caplog):
    app, items = create_app_with_immich_cache(sample_config[0])
    app.run_jobs(False, False)
    assert "Show" not in caplog.text
    assert "Group" not in caplog.text
    assert str(items[0]["id"]) not in caplog.text
    assert items[0]["file"] not in caplog.text
    assert f"'file' = '{items[0]['file']}'" not in caplog.text


def test_application_show(sample_config, caplog):
    app, items = create_app_with_immich_cache(sample_config[0])
    app.run_jobs(True, False)
    assert "Show" in caplog.text
    assert "Group" not in caplog.text
    assert str(items[0]["id"]) in caplog.text
    assert items[0]["file"] in caplog.text
    assert f"'file' = '{items[0]['file']}'" not in caplog.text


def test_application_group(sample_config, caplog):
    app, items = create_app_with_immich_cache(sample_config[0])
    app.run_jobs(False, True)
    assert "Show" in caplog.text
    assert "Group" in caplog.text
    assert str(items[0]["id"]) in caplog.text
    assert items[0]["file"] in caplog.text
    assert f"'file' = '{items[0]['file']}'" in caplog.text


def test_application_compare_missing_baseline(sample_config):
    app = Application(sample_config[0], True)
    app.load_job("sub")
    with pytest.raises(ValueError):
        app.compare("main", "sub")


def test_application_compare_missing_compare(sample_config):
    app = Application(sample_config[0], True)
    app.load_job("main")
    with pytest.raises(ValueError):
        app.compare("main", "sub")


def test_application_compare(sample_config, caplog):
    app, _ = create_app_with_immich_cache(sample_config[0])
    app.load_job("empty")
    app.run_jobs(False, False)
    app.compare("main", "empty")
    assert "1 assets present only in baseline" in caplog.text


def test_application_writes_gpx(sample_config):
    app = Application(sample_config[0], True)
    app.load_job("main")
    app.run_jobs(False, False)
    app.export_gpx()
    path_main = sample_config[1] / "main.gpx"
    path_sub = sample_config[1] / "sub.gpx"
    assert path_main.exists()
    assert not path_sub.exists()


def test_application_use_existing_writer(sample_config):
    app = Application(sample_config[0], True)
    app.load_job("main")
    app.run_jobs(False, False)
    app.export_gpx()
    path_main = sample_config[1] / "main.gpx"
    path_sub = sample_config[1] / "sub.gpx"
    assert path_main.exists()
    assert not path_sub.exists()
    app.load_job("sub")
    app.run_jobs(False, False)
    app.export_gpx()
    path_sub = sample_config[1] / "sub.gpx"
    assert path_sub.exists()
