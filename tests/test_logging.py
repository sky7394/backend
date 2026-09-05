import logging
from app.core.logging import logger, setup_logging

def test_logger_instance():
    assert isinstance(logger, logging.Logger)
    assert logger.name == "gapcode"

def test_setup_logging_idempotent():
    first_handler_count = len(logger.handlers)
    re_logger = setup_logging()
    assert re_logger.name == "gapcode"
    # Handler count should not duplicate on multiple calls
    assert len(re_logger.handlers) == first_handler_count

def test_logger_emits_info(caplog):
    with caplog.at_level(logging.INFO, logger="gapcode"):
        logger.info("Audit log test message: event=test_event user_id=123")
    assert "Audit log test message" in caplog.text
