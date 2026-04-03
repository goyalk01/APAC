from functools import lru_cache
from importlib import import_module

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Multi-Agent Productivity Assistant"
    environment: str = "dev"
    api_prefix: str = "/v1"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 120

    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    vertex_model_name: str = "gemini-1.5-pro-002"
    vertex_max_steps: int = 6
    allow_local_function_call_stub: bool = False

    mcp_server_url: str = "http://localhost:9000"

    enable_firestore: bool = False
    firestore_database: str = "(default)"
    rate_limit_requests_per_minute: int = 60

    jwt_secret_secret_name: str = ""

    def resolve_jwt_secret(self) -> str:
        if self.environment.lower() != "prod":
            return self.jwt_secret
        if self.jwt_secret:
            return self.jwt_secret
        if not self.jwt_secret_secret_name or not self.google_cloud_project:
            raise ValueError("JWT secret must come from Secret Manager in prod")

        secretmanager = import_module("google.cloud.secretmanager")
        client = secretmanager.SecretManagerServiceClient()
        resource = f"projects/{self.google_cloud_project}/secrets/{self.jwt_secret_secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": resource})
        return response.payload.data.decode("utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
