from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    # GCP
    gcp_project_id: str
    gcp_location: str = "us"
    gcp_processor_id: str
    gcs_bucket_name: str

    # Firestore
    firestore_database: str = "(default)"

    # App
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit: str = "10/minute"
    max_file_size_mb: int = 20
    min_image_width: int = 400
    min_image_height: int = 300
    min_image_file_size_kb: int = 20

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }
