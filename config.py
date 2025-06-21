from enum import Enum


class AppSettings(Enum):
    """Settings for the application."""

    DB_FILE = "ssa.db"
    DOWNLOAD_DIR = "pdf_downloads"
