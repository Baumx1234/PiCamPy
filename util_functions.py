import logging
import os


def setup_logging(log_filename, log_level):
    """Configure logging with both console and file output."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(script_dir, log_filename)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),  # For systemd/journalctl
            logging.FileHandler(log_file),  # For logging to a file
        ],
        force=True,  # Override existing configuration
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - log file: {log_file}")
    return logger
