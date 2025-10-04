import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import os

LOG_DIR = Path(os.getenv("LOG_PATH", Path(__file__).parent.parent / "logs"))
LOG_DIR.mkdir(exist_ok=True, parents=True)

class Logger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.logger = logging.getLogger("pgx-lower")
        self.logger.setLevel(logging.INFO)

        if self.logger.handlers:
            return

        file_handler = RotatingFileHandler(
            LOG_DIR / "backend.log",
            maxBytes=10 * 1024 * 1024,  
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, message: str):
        self.logger.info(message)

    def error(self, message: str):
        self.logger.error(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def debug(self, message: str):
        self.logger.debug(message)

logger = Logger()
