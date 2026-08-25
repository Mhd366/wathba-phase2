from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "WATHBA Federation Trial API"
    app_env: str = "development"
    contract_version: str = "2.0.0"
    model_mode: str = "mock"
    model_version: str = "training"
    model_path: str = "/models/wathba-pose-v1.onnx"
    allowed_origins: str = "http://localhost:3000"
    chat_integration_url: str = ""
    recommendations_integration_url: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

