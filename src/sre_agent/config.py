from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    aws_region: str = "us-east-1"
    model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    log_level: str = "INFO"
    max_log_events: int = 100
    log_lookback_minutes: int = 60
    aws_allowed_log_group_prefixes: str = "/aws/"
    approval_hmac_secret: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_log_prefixes(self) -> tuple[str, ...]:
        return tuple(x.strip() for x in self.aws_allowed_log_group_prefixes.split(",") if x.strip())

settings = Settings()
