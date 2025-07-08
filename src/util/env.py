"""Environment variable loader for the spot hedging bot."""

import os
from pathlib import Path
from typing import Optional

from loguru import logger


def load_env_from_file(file_path: str = "configs/secrets.env") -> None:
    """Load environment variables from a .env file.

    Args:
        file_path: Path to the .env file
    """
    env_file = Path(file_path)

    if not env_file.exists():
        logger.warning(f"Environment file {file_path} not found")
        return

    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key] = value
                logger.debug(f"Loaded environment variable: {key}")


def get_telegram_token() -> Optional[str]:
    """Get the Telegram bot token from environment variables.

    Returns:
        The Telegram bot token or None if not found
    """
    return os.getenv("TELEGRAM_TOKEN")


def validate_environment() -> bool:
    """Validate that all required environment variables are set.

    Returns:
        True if all required variables are set, False otherwise
    """
    required_vars = ["TELEGRAM_TOKEN"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return False

    logger.info("All required environment variables are set")
    return True


# Load environment variables on module import
load_env_from_file()
