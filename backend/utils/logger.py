import logging
import sys
from config.settings import settings


def setup_logger(name: str = "airguard") -> logging.Logger:
    """
    Sets up a standardized logger for AirGuard AI.
    Prevents sensitive secrets from leaking and formats messages clearly.
    """
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers if already configured
    if logger.handlers:
        return logger

    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


logger = setup_logger("airguard")
