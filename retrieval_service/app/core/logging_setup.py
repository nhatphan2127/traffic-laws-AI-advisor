import logging.config

import yaml

from app.core.config import BASE_DIR, CONFIG_DIR

_configured = False


def setup_logging():
    """Configure logging from config/logger.yaml once per process."""
    global _configured
    if _configured:
        return

    with open(CONFIG_DIR / "logger.yaml", "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    for handler in config.get("handlers", {}).values():
        if "filename" in handler:
            handler["filename"] = str(BASE_DIR / handler["filename"])

    logging.config.dictConfig(config)
    _configured = True
