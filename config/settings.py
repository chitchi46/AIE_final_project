from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    """Project configuration"""
    OPENAI_API_KEY: str = ""
    UPLOAD_DIR: Path = Path("data/uploads")
    FAISS_INDEX_DIR: Path = Path("data/faiss_index")

settings = Settings()
