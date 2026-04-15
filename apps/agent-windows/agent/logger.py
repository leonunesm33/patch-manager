import logging
from pathlib import Path

from config import AgentConfig


def configure_logging(config: AgentConfig) -> logging.Logger:
    logger = logging.getLogger("patch_manager_agent_windows")
    logger.setLevel(getattr(logging, config.log_level, logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    if config.log_to_stdout:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    if config.log_file:
        log_path = Path(config.log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
