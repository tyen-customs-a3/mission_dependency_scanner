import logging
import subprocess

logger = logging.getLogger(__name__)

def setup_logging(debug: bool = False):
    """Configure logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('dependency_scanner')

def check_mikero_tools() -> bool:
    """Check if mikero's tools (specifically ExtractPbo) are available in PATH."""
    try:
        subprocess.run(['ExtractPbo', '-P'], capture_output=True)
        return True
    except FileNotFoundError:
        return False
