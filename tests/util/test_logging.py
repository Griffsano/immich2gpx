import logging

import pytest

from immich2gpx.utils.logging import configure_logging


def test_configure_logging_debug():
    configure_logging("DEBUG")
    logger = logging.getLogger()
    assert logger.getEffectiveLevel() == logging.DEBUG


def test_configure_logging_default():
    configure_logging()
    logger = logging.getLogger()
    assert logger.getEffectiveLevel() == logging.INFO


def test_configure_logging_invalid():
    with pytest.raises(ValueError):
        configure_logging("INVALID")  # type: ignore


def test_configure_logging_handle_clearing():
    root_logger = logging.getLogger()
    dummy_handler = logging.NullHandler()
    root_logger.addHandler(dummy_handler)
    assert dummy_handler in root_logger.handlers
    configure_logging()
    assert dummy_handler not in root_logger.handlers
    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0], logging.StreamHandler)
    root_logger.handlers.clear()
    configure_logging()
    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0], logging.StreamHandler)
