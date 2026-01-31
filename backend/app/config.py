from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "crawler_experiment"
    backend_port: int = 8001
    max_pages: int = 15
    request_delay: float = 1.0
    playwright_timeout: int = 15000
    min_body_length: int = 500

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
