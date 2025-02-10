import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

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
        cache_file = cache_dir / f"{key}.json"
        cache_file.write_text(json.dumps({
            "timestamp": time.time(),
            "data": data
        }))
        logger.info(f"Cache saved: {cache_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save cache: {e}")
        return False

def load_cache(cache_dir: Path, key: str) -> Optional[Dict[str, Any]]:
    """Load data from cache file if it exists."""
    try:
        cache_file = cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
            
        data = json.loads(cache_file.read_text())
        logger.info(f"Cache loaded: {cache_file}")
        return data.get("data")
    except Exception as e:
        logger.error(f"Failed to load cache: {e}")
        return None
