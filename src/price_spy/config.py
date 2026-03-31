from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/price_spy"

    scrape_concurrency: int = 3
    scrape_timeout: int = 30000
    scrape_retry_count: int = 3
    scrape_daily_hour: int = 7

    max_baskets_per_user: int = 10
    max_items_per_basket: int = 50
    price_history_retention_days: int = 90

    log_level: str = "INFO"

    @property
    def database_url_async(self) -> str:
        """Async URL for SQLAlchemy async engine (always uses asyncpg)."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def database_url_sync(self) -> str:
        """Sync URL for APScheduler jobstore (APScheduler 3.x needs sync)."""
        url = self.database_url
        # Strip any async driver suffix
        url = url.replace("+asyncpg", "")
        # Normalize postgres:// to postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()  # type: ignore[call-arg]
