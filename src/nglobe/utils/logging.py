"""Structured logging setup for NetworkGlobe.

Uses structlog for structured, context-rich logging throughout the application.
Supports both human-readable ("pretty") and machine-parseable ("structured")
output formats, configurable via config.toml.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from nglobe.config import LoggingConfig


def setup_logging(config: LoggingConfig) -> None:
    """Configure structlog and stdlib logging.

    Args:
        config: Logging configuration section from AppConfig.
    """
    log_level = getattr(logging, config.level.upper(), logging.INFO)

    # Choose processors based on output format
    if config.format == "structured":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(
            colors=sys.stderr.isatty(),
        )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # File handler — the only trace left when launched by double-click
    try:
        log_path = Path(config.file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=config.max_size_mb * 1024 * 1024,
            backupCount=config.backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(colors=False),
                ],
                foreign_pre_chain=shared_processors,
            )
        )
        root_logger.addHandler(file_handler)
    except OSError as e:
        print(f"Log file unavailable: {e}", file=sys.stderr)
    root_logger.setLevel(log_level)

    # Quiet noisy third-party loggers
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "mitmproxy"):
        logging.getLogger(name).setLevel(max(log_level, logging.WARNING))


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a bound logger for the given module name.

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        A structlog BoundLogger with the module name bound.
    """
    return structlog.get_logger(name)
