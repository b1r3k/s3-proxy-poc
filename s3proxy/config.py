import __main__
from pydantic_settings import BaseSettings, SettingsConfigDict

from .version import __version__

print(__main__.__package__)


class GlobalSettings(BaseSettings):
    model_config = SettingsConfigDict(
        # `.env.prod` takes priority over `.env`
        env_file=(".env", ".env.prod"),
        extra="ignore",
    )

    APP_NAME: str = str(__main__.__package__)
    APP_VERSION: str = __version__
    SENTRY_DSN: str | None = None
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_S3_ENDPOINT_URL: str | None = None
    B2_APP_KEY_ID: str | None = None
    B2_APP_KEY: str | None = None


settings = GlobalSettings()


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s [%(name)s:%(lineno)d] %(message)s",
            "datefmt": "%d-%m-%Y %I:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": settings.LOG_LEVEL,
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": settings.LOG_LEVEL,
            "propagate": True,
        },
        "app": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "gunicorn.access": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
