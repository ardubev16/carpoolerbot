from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    TELEGRAM_TOKEN: str = Field(default=...)
    DB_HOST: str = Field(default=...)
    DB_NAME: str = Field(default=...)
    DB_USERNAME: str = Field(default=...)
    DB_PASSWORD: str = Field(default="sqlite://")

    @computed_field
    @property
    def db_url(self) -> str:
        return f"postgresql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:5432/{self.DB_NAME}"


settings = Settings()
