import logging
import sys


def setup_logging() -> None:
    """Configure logging to output to both the console and a file."""
    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Console logger
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Create a simple formatter for the console
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)

    if not logger.handlers:
        logger.addHandler(console_handler)
