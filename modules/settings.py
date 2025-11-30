import os
from functools import lru_cache
from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str = Field(..., description="Supabase URL")
    SUPABASE_KEY: SecretStr = Field(..., description="Supabase Service Role Key or Anon Key")

    # Email
    EMAIL_HOST: str = Field("smtp.example.com", description="SMTP Host")
    EMAIL_PORT: int = Field(587, description="SMTP Port")
    EMAIL_USER: str = Field("notify@example.com", description="SMTP User")
    EMAIL_PASSWORD: SecretStr = Field(SecretStr("supersecret"), description="SMTP Password")
    EMAIL_FROM_NAME: str = Field("Clinic Assistant", description="Email From Name")

    # AI
    GROQ_API_KEY: Optional[SecretStr] = Field(None, description="Groq API Key")

    # App
    DEBUG: bool = Field(False, description="Debug mode")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
