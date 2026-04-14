"""Configuración centralizada del sistema mediante pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Parámetros de configuración cargados desde .env o variables de entorno."""

    # Base de datos
    DATABASE_URL: str = "postgresql+psycopg2://logpuller:password@localhost:5432/logpuller"

    # Directorio de logs a monitorizar
    LOG_DIR: Path = Path("/var/logs")
    LOG_EXTENSIONS: str = ".log,.txt,.out"

    # Procesamiento
    BATCH_SIZE: int = 500
    MAX_FILE_SIZE_MB: int = 500

    # Logging de la aplicación
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path = Path("logs/logpuller.log")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def extensiones_validas(self) -> list[str]:
        """Devuelve la lista de extensiones de fichero permitidas."""
        return [ext.strip() for ext in self.LOG_EXTENSIONS.split(",")]


settings = Settings()
