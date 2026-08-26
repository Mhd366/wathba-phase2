from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "WATHBA Federation Trial API"
    app_env: str = "development"
    contract_version: str = "2.0.0"
    model_mode: str = "mock"
    model_version: str = "training"
    model_path: str = "/tmp/wathba-pose-v1.pt"
    model_bucket: str = "model-artifacts"
    model_object_path: str = "production/best.pt"
    model_object_parts: str = ""
    model_sha256: str = "0683621EC60D20218F137542808EB6E7EA09A77291C23866DF1F3B2BF87CBFB4"
    model_size_bytes: int = 118267057
    model_confidence: float = 0.30
    keypoint_confidence: float = 0.35
    model_max_frames: int = 1500
    lane_order_top_to_bottom: bool = True
    minimum_track_frames: int = 12
    video_bucket: str = "race-videos"
    database_url: str = ""
    allowed_origins: str = "http://localhost:3000"
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_service_role_key: str = ""
    chat_integration_url: str = ""
    recommendations_integration_url: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
