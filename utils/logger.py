"""One log file per process to avoid xdist file-handler collisions."""

import logging
import os
from pathlib import Path


def configure_logging(logs_dir: Path) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    worker = os.getenv("PYTEST_XDIST_WORKER", "main")
    filename = "automation.log" if worker == "main" else f"automation-{worker}.log"
    logger = logging.getLogger("automation")
    logger.setLevel(logging.INFO)
    logger.propagate = True  # Keep pytest's captured logs in failure reports.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    handler = logging.FileHandler(logs_dir / filename, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            f"%(asctime)s | %(levelname)-8s | {worker} | %(name)s | %(message)s"
        )
    )
    logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"automation.{name}")
