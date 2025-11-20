"""
Configuration management for Team Synapse.
Handles all environment variables and application settings.
"""
import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

@dataclass
class GoogleCloudConfig:
    """Google Cloud Platform configuration."""
    project_id: str
    location: str
    gcs_bucket_name: str
    credentials_path: Optional[str]

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.gcs_bucket_name == "YOUR_GCS_BUCKET_NAME_HERE":
            raise ValueError(
                "GCS_BUCKET_NAME must be set. Please configure your Google Cloud Storage bucket."
            )
        
        if not self.credentials_path and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            raise ValueError(
                "Google Cloud credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS "
                "environment variable or provide credentials_path."
            )


@dataclass
class GeminiConfig:
    """Gemini model configuration."""
    model_name: str = "gemini-2.5-pro"
    temperature: float = 0.1
    max_output_tokens: int = 8192


@dataclass
class Neo4jConfig:
    """Neo4j database config."""
    uri: str
    username: str
    password: str
    database: str = "neo4j" # default

    def __post_init__(self):
        if self.uri == "YOUR_NEO4J_URI_HERE":
            raise ValueError(
                "NEO4J_URI must be set. Please configure your Neo4j AuraDB instance."
            )
        if not self.username or not self.password:
            raise ValueError(
                "NEO4J_USERNAME and NEO4J_PASSWORD must be set."
            )

@dataclass
class AppConfig:
    """Application-wide configuration."""
    max_file_size_mb: int = 100
    allowed_audio_formats: tuple = (".mp3", ".wav", ".m4a", ".ogg")
    log_level: str = "INFO"
    neo4j_enabled: bool = True

class Config:
    """Main configuration class."""
    
    def __init__(self):
        self.google_cloud = GoogleCloudConfig(
            project_id=os.getenv("VERTEX_PROJECT_ID", "YOUR_PROJECT_ID"),
            location=os.getenv("VERTEX_LOCATION", "us-central1"),
            gcs_bucket_name=os.getenv("GCS_BUCKET_NAME", "YOUR_GCS_BUCKET_NAME_HERE"),
            credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )
        
        self.gemini = GeminiConfig(
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
            temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.1")),
            max_output_tokens=int(os.getenv("GEMINI_MAX_TOKENS", "8192"))
        )
        
        self.neo4j = Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "YOUR_NEO4J_URI_HERE"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password")
        )
        
        self.app = AppConfig(
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "100")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            neo4j_enabled=os.getenv("NEO4J_ENABLED", "True") == "True"
        )
    
    def validate(self) -> bool:
        """Validate all configuration settings."""
        try:
            # Google Cloud config validates in __post_init__
            return True
        except ValueError as e:
            print(f"Configuration error: {e}")
            return False


# Global configuration instance
config = Config()