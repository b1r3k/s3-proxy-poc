import logging

from .config import LOGGING_CONFIG, settings

logging.config.dictConfig(LOGGING_CONFIG)

root_logger = logging.getLogger(settings.APP_NAME)
