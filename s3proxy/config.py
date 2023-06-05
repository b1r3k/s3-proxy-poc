from os import environ

from pydantic import BaseSettings


class GlobalSettings(BaseSettings):
    ENVIRONMENT: str = "local"
    DEBUG: bool = environ.get("DEBUG", False)
    LOG_LEVEL: str = environ.get("LOG_LEVEL", "INFO")
    AWS_ACCESS_KEY_ID: str = environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = environ.get("AWS_SECRET_ACCESS_KEY")
    B2_APP_KEY_ID: str = environ.get("B2_APP_KEY_ID")
    B2_APP_KEY: str = environ.get("B2_APP_KEY")

    def is_local(self) -> bool:
        return self.ENVIRONMENT in ["local", "test"]


settings = GlobalSettings()
