import os
from typing import List, Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    
    # Database Configuration
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    
    # JWT Configuration
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    
    # CORS Configuration
    cors_origins: List[str] = ["http://localhost:3000"]
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    
    # File Storage Configuration
    storage_path: str = "/app/storage"
    max_file_size: int = 1073741824  # 1GB
    allowed_file_types: List[str] = [
        "image/jpeg", "image/png", "image/tiff", 
        "application/zip", "text/plain"
    ]
    
    # WebODM Configuration
    webodm_api_url: Optional[str] = None
    webodm_api_token: Optional[str] = None
    webodm_timeout: int = 300  # 5 minutes
    
    # Google Earth Engine Configuration
    google_application_credentials: Optional[str] = None
    gee_project_id: Optional[str] = None
    
    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379"
    celery_result_backend: str = "redis://localhost:6379"
    celery_task_serializer: str = "json"
    celery_result_serializer: str = "json"
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Monitoring Configuration
    enable_metrics: bool = True
    metrics_port: int = 9090
    
    @validator("debug", pre=True)
    def set_debug(cls, v, values):
        return values.get("environment", "").lower() == "development"
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("allowed_hosts", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Service-specific settings
class AuthServiceSettings(Settings):
    service_name: str = "auth-service"
    service_port: int = 8001


class FileServiceSettings(Settings):
    service_name: str = "file-service"
    service_port: int = 8002


class WebODMServiceSettings(Settings):
    service_name: str = "webodm-service"
    service_port: int = 8003


class GEEServiceSettings(Settings):
    service_name: str = "gee-service"
    service_port: int = 8004


class ProcessingServiceSettings(Settings):
    service_name: str = "processing-service"
    service_port: int = 8005


class AnalysisServiceSettings(Settings):
    service_name: str = "analysis-service"
    service_port: int = 8006


class VisualizationServiceSettings(Settings):
    service_name: str = "visualization-service"
    service_port: int = 8007


class APIGatewaySettings(Settings):
    service_name: str = "api-gateway"
    service_port: int = 8000
    
    # Service URLs for routing
    auth_service_url: str = "http://auth-service:8001"
    file_service_url: str = "http://file-service:8002"
    webodm_service_url: str = "http://webodm-service:8003"
    gee_service_url: str = "http://gee-service:8004"
    processing_service_url: str = "http://processing-service:8005"
    analysis_service_url: str = "http://analysis-service:8006"
    visualization_service_url: str = "http://visualization-service:8007"


# Factory function to get settings based on service
def get_settings(service_name: str = None) -> Settings:
    """Get settings instance based on service name"""
    settings_map = {
        "auth-service": AuthServiceSettings,
        "file-service": FileServiceSettings,
        "webodm-service": WebODMServiceSettings,
        "gee-service": GEEServiceSettings,
        "processing-service": ProcessingServiceSettings,
        "analysis-service": AnalysisServiceSettings,
        "visualization-service": VisualizationServiceSettings,
        "api-gateway": APIGatewaySettings,
    }
    
    if service_name and service_name in settings_map:
        return settings_map[service_name]()
    
    return Settings()


# Global settings instance
settings = get_settings(os.getenv("SERVICE_NAME"))