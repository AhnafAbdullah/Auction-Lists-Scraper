import logging
import os
from pathlib import Path


def setup_logger():
    log_file = 'auction_scraper_errors.log'

    # 1. Close and remove any existing file handlers
    for handler in logging.root.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            logging.root.removeHandler(handler)

    # 2. Now safely delete the old log file
    try:
        Path(log_file).unlink(missing_ok=True)
    except PermissionError:
        pass  # Skip if still locked

    # 3. Configure fresh logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    # Silence webdriver_manager logs
    logging.getLogger('WDM').setLevel(logging.WARNING)

    return logging.getLogger('scraper')