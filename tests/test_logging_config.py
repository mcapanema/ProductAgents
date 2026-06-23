"""Tests for the file-based logging configuration."""

import logging
from logging.handlers import RotatingFileHandler

from productagents.core import logging_config


def _pa_file_handlers():
    pa = logging.getLogger("productagents")
    return [h for h in pa.handlers if getattr(h, "_productagents_handler", False)]


def test_configure_logging_writes_records_to_file(tmp_path, monkeypatch):
    logfile = tmp_path / "pa.log"
    monkeypatch.setenv("PRODUCTAGENTS_LOG_FILE", str(logfile))
    monkeypatch.delenv("PRODUCTAGENTS_LOG_LEVEL", raising=False)

    path = logging_config.configure_logging()

    assert path == logfile
    logging.getLogger("productagents.demo").info("hello-marker")
    for handler in _pa_file_handlers():
        handler.flush()
    assert "hello-marker" in logfile.read_text()


def test_configure_logging_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_LOG_FILE", str(tmp_path / "pa.log"))
    monkeypatch.delenv("PRODUCTAGENTS_LOG_LEVEL", raising=False)

    logging_config.configure_logging()
    logging_config.configure_logging()

    handlers = _pa_file_handlers()
    assert len(handlers) == 1
    assert isinstance(handlers[0], RotatingFileHandler)


def test_log_level_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_LOG_FILE", str(tmp_path / "pa.log"))
    monkeypatch.setenv("PRODUCTAGENTS_LOG_LEVEL", "DEBUG")

    logging_config.configure_logging()

    assert logging.getLogger("productagents").level == logging.DEBUG


def test_invalid_log_level_falls_back_to_info(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_LOG_FILE", str(tmp_path / "pa.log"))
    monkeypatch.setenv("PRODUCTAGENTS_LOG_LEVEL", "NONSENSE")

    logging_config.configure_logging()

    assert logging.getLogger("productagents").level == logging.INFO


def test_logger_does_not_propagate_to_root(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTAGENTS_LOG_FILE", str(tmp_path / "pa.log"))
    monkeypatch.delenv("PRODUCTAGENTS_LOG_LEVEL", raising=False)

    logging_config.configure_logging()

    # The TUI owns the terminal; logs must never reach root's stderr handler.
    assert logging.getLogger("productagents").propagate is False
