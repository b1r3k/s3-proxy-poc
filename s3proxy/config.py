from os import environ

from pydantic import BaseSettings


class GlobalSettings(BaseSettings):
    ENVIRONMENT: str = "local"
    DEBUG: bool = False
    B2_APP_KEY_ID: str = environ.get("B2_APP_KEY_ID")
    B2_APP_KEY: str = environ.get("B2_APP_KEY")

    def is_local(self) -> bool:
        return self.ENVIRONMENT in ["local", "test"]


settings = GlobalSettings()
