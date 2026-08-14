__version__ = "0.1.0"
__author__ = "Libin, QuestYard HuRAG Team"
__description__ = "Alaya, A HuRAG based chatbot web application from QuestYard."
__url__ = "https://github.com/QuestYard/Alaya"

import yaml
import logging

from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

from .utilities import dict_to_namespace

load_dotenv(Path.cwd() / ".env")

# -- Global Variables --

logger: logging.Logger = logging.getLogger("alaya")
logger.propagate = False
logger.setLevel(logging.DEBUG)

conf: Any

# -- Initialization --

def load_config() -> Any:
    try:
        config_path = Path.cwd() / "alaya.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        config = dict_to_namespace(data)

        # Ensure config is not a list (which dict_to_namespace can return)
        if isinstance(config, list):
            raise ValueError("Config file must be a dictionary, not a list")

        if config.db.user is None:
            raise ValueError("Missing required configuration: db.user")
        if config.db.password is None:
            raise ValueError("Missing required configuration: db.password")
        if config.db.database is None:
            raise ValueError("Missing required configuration: db.database")
        if config.service.agent_model is None:
            raise ValueError("Missing required configuration: service.agent_model")

        config.db.host = config.db.host or "localhost"
        config.db.port = config.db.port or 3306
        config.app.ctx_size = config.app.ctx_size or "large"
        config.app.host = config.app.host or "0.0.0.0"
        config.app.port = config.app.port or 8000
        config.service.hurag_server = (
            config.service.hurag_server or "http://localhost:5002/v1/tools"
        )
        return config
    except ValueError as ve:
        raise ve
    except Exception as e:
        raise RuntimeError(f"Config file not exists or invalid: {e}")


# Load configuration
conf = load_config()

# Configure Logger Handlers
fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s - %(message)s")
console_handler = logging.StreamHandler()
console_handler.setFormatter(fmt)
console_handler.setLevel(logging.WARNING)
logger.addHandler(console_handler)

file_handler = RotatingFileHandler(
    filename=Path.cwd() / "alaya.log",
    maxBytes= 10485760,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setFormatter(fmt)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# -- Shortcuts --

__all__ = ["conf", "logger"]
