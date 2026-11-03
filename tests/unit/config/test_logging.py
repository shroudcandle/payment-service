from __future__ import annotations

import logging

from payment_service.config import CorrelationIdFilter, configure_logging


def test_filter_defaults_missing_correlation_id() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "msg", (), None)

    assert CorrelationIdFilter().filter(record) is True
    assert record.correlation_id == "-"


def test_filter_keeps_existing_correlation_id() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "msg", (), None)
    record.correlation_id = "trace-1"

    assert CorrelationIdFilter().filter(record) is True
    assert record.correlation_id == "trace-1"


def test_configure_logging_installs_stream_handler() -> None:
    root = logging.getLogger()
    previous_handlers = list(root.handlers)
    previous_level = root.level
    try:
        configure_logging("DEBUG")

        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1
        handler = root.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert any(isinstance(item, CorrelationIdFilter) for item in handler.filters)
    finally:
        root.handlers[:] = previous_handlers
        root.setLevel(previous_level)
