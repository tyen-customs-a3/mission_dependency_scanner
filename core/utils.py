import sys
import logging
from pathlib import Path

def setup_module_paths():
    """Setup paths for external module dependencies."""
    base_dir = Path(__file__).parent.parent.parent
    module_paths = [
        base_dir / "asset_scanner/src",
        base_dir / "ini_class_parser/src",
        base_dir / "mission_scanner/src"
    ]
    
    for path in module_paths:
        abs_path = path.resolve()
        if abs_path.exists() and str(abs_path) not in sys.path:
            sys.path.insert(0, str(abs_path))

def setup_logging(debug: bool = False):
    """Configure logging for the application."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('dependency_scanner')
