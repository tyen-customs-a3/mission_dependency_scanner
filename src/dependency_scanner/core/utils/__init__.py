from pathlib import Path
import logging
import subprocess
import os
import hashlib
import json
import time
from typing import Dict, Any, Optional

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

def calculate_folder_hash(folder_path: Path) -> str:
    """Calculate a hash based on folder modification times and sizes."""
    if not folder_path.exists():
        return ""
        
    hash_content = []
    
    try:
        for root, _, files in os.walk(folder_path):
            for file in sorted(files):  # Sort for consistency
                file_path = Path(root) / file
                stats = file_path.stat()
                # Combine mtime and size for quick hash
                hash_content.append(f"{file_path}:{stats.st_mtime}:{stats.st_size}")
    except Exception as e:
        logger.warning(f"Error walking folder {folder_path}: {e}")
        return ""
        
    content_str = "|".join(hash_content)
    return hashlib.md5(content_str.encode()).hexdigest()

def get_cache_key(folder_path: Path) -> str:
    """Generate a cache key from folder name and hash."""
    folder_hash = calculate_folder_hash(folder_path)
    return f"{folder_path.name}_{folder_hash[:8]}"

def save_cache(cache_dir: Path, key: str, data: Dict[str, Any]) -> bool:
    """Save data to cache file."""
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{key}.json"
        
        # Ensure we can serialize the data
        cache_data = {
            "timestamp": time.time(),
            "data": {
                class_name: {
                    "name": str(class_info.name),
                    "parent": str(class_info.parent),
                    "properties": {k: str(v) for k, v in class_info.properties.items()}
                }
                for class_name, class_info in data.items()
            }
        }
        
        cache_file.write_text(json.dumps(cache_data, indent=2))
        logger.info(f"Cache saved: {cache_file} ({len(data)} classes)")
        return True
    except Exception as e:
        logger.error(f"Failed to save cache: {e}", exc_info=True)
        return False

def load_cache(cache_dir: Path, key: str) -> Optional[Dict[str, Any]]:
    """Load data from cache file if it exists."""
    try:
        cache_file = cache_dir / f"{key}.json"
        if not cache_file.exists():
            logger.debug(f"No cache file found: {cache_file}")
            return None
            
        cache_data = json.loads(cache_file.read_text())
        logger.info(f"Cache loaded: {cache_file}")
        return cache_data.get("data")
    except Exception as e:
        logger.error(f"Failed to load cache: {e}", exc_info=True)
        return None
