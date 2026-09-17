import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    GROQ_API_KEY_2: str = ""
    DEFAULT_MODEL: str = "openai/gpt-oss-120b"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemma-4-31b-it:free"
    CONCURRENCY: int = 10
    NEON_DATABASE_URL: str = ""
    
    @property
    def groq_keys(self) -> list[str]:
        keys = []
        if self.GROQ_API_KEY: keys.append(self.GROQ_API_KEY)
        if self.GROQ_API_KEY_2: keys.append(self.GROQ_API_KEY_2)
        return keys

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    
settings = Settings()
