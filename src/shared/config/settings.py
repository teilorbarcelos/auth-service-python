from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    jwt_secret: str = Field(alias="JWT_SECRET")
    environment: str = Field(default="local", alias="ENVIRONMENT")
    port: int = Field(default=8001, alias="PORT")
    first_user: str = Field(default="admin@email.com", alias="FIRST_USER")
    first_password: str = Field(default="admin123", alias="FIRST_PASSWORD")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    rate_limit_max: int = Field(default=60, alias="RATE_LIMIT_MAX")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    jwt_issuer: str = Field(default="backend-python", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="backend-python-api", alias="JWT_AUDIENCE")
    jwt_access_expiration_hours: int = Field(default=24, alias="JWT_ACCESS_EXPIRATION_HOURS")
    jwt_refresh_expiration_days: int = Field(default=7, alias="JWT_REFRESH_EXPIRATION_DAYS")
    password_bcrypt_cost: int = Field(default=12, alias="PASSWORD_BCRYPT_COST")
    cors_allowed_origins: str = Field(default="http://localhost:3000", alias="CORS_ALLOWED_ORIGINS")

    bootstrap_auth: bool = Field(default=True, alias="BOOTSTRAP_AUTH")

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str, info):
        if info.data.get("environment") == "production" and len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters in production")
        return v

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
