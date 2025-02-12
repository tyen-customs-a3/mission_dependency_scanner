from pathlib import Path
import hashlib
from typing import Dict, Union, Any, cast, Tuple, TypeVar, Mapping
import logging
import os

from asset_scanner import AssetAPI
from class_scanner import ClassAPI
from class_scanner.models import ClassData
from asset_scanner.models import Asset
from asset_scanner.config import APIConfig

logger = logging.getLogger(__name__)

def calculate_folder_hash(folder_path: Path) -> str:
    """Calculate a hash based on recursive folder contents."""
    if not folder_path.exists():
        return ""
    
    try:
        total_size = 0
        latest_mtime: int = 0
        
        for root, _, files in os.walk(folder_path):
            for file in files:
                stats = (Path(root) / file).stat()
                total_size += stats.st_size
                latest_mtime = max(latest_mtime, int(stats.st_mtime))
                
        return hashlib.md5(f"{folder_path}:{total_size}:{latest_mtime}".encode()).hexdigest()
        
    except Exception as e:
        logger.warning(f"Error calculating folder hash for {folder_path}: {e}")
        return ""

def get_cache_key(game_data: str, task: str) -> str:
    """Generate a cache key from game data and task."""
    return f"{game_data}_{task}"

def is_cache_valid(cache_dir: Path, game_data: str, task: str) -> bool:
    """Check if cache exists and is valid for the given game data and task."""
    try:
        key = get_cache_key(game_data, task)
        class_cache = cache_dir / "classes" / f"{key}.json"
        asset_cache = cache_dir / "assets" / f"{key}.json"
        
        if not class_cache.exists() or not asset_cache.exists():
            logger.debug(f"No cache files found for {game_data} {task}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error checking cache validity: {e}")
        return False

def _normalize_path(path: Union[str, Path]) -> str:
    """Normalize path string for consistent caching."""
    return str(path).replace('\\', '/')

CacheableData = Dict[str, Union[ClassData, Asset]]
T = TypeVar('T', bound=Mapping[str, Any])

class CacheManager:
    """Manages caching using the specialized APIs."""
    
    def __init__(self, cache_dir: Path):
        """Initialize cache structure."""
        self.cache_dir = cache_dir
        self.class_cache_dir = cache_dir / "classes"
        self.asset_cache_dir = cache_dir / "assets"
        
        # Create specialized cache directories
        self.base_game_dir = cache_dir / "base_game"
        self.tasks_dir = cache_dir / "tasks"
        
        # Ensure all cache directories exist
        for directory in (self.class_cache_dir, self.asset_cache_dir, 
                        self.base_game_dir, self.tasks_dir):
            directory.mkdir(parents=True, exist_ok=True)
        
        self._default_class_api = ClassAPI(cache_dir=self.class_cache_dir)
        self._default_asset_api = AssetAPI(config=APIConfig(
            cache_file=self.asset_cache_dir / "asset_cache.json",
            max_cache_size=10000000
        ))

    def create_apis(self, task_dir: Path) -> Tuple[ClassAPI, AssetAPI]:
        """Create new API instances for specific directory."""
        class_cache_dir = task_dir / "classes"
        asset_cache_dir = task_dir / "assets"
        
        class_cache_dir.mkdir(parents=True, exist_ok=True)
        asset_cache_dir.mkdir(parents=True, exist_ok=True)
        
        return (
            ClassAPI(cache_dir=class_cache_dir),
            AssetAPI(config=APIConfig(
                cache_file=asset_cache_dir / "asset_cache.json",
                max_cache_size=10000000
            ))
        )

    def save_cache(self, key: str, data: CacheableData, task: str = "") -> bool:
        """Save data to appropriate cache location."""
        try:
            # Determine cache location based on key/task
            if key == "base_game":
                cache_dir = self.base_game_dir
            else:
                cache_dir = self.tasks_dir / task if task else self.tasks_dir
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Create task-specific APIs
            class_api, asset_api = self.create_apis(cache_dir)
            
            # Split data into classes and assets
            class_data = {k: v for k, v in data.items() if isinstance(v, ClassData)}
            asset_data = {k: v for k, v in data.items() if isinstance(v, Asset)}
            
            # Save class data
            if class_data:
                class_cache = cache_dir / f"{key}_classes.json"
                class_api.cache.add_classes(class_data)
                class_api.cache.save_to_disk(class_cache)
            
            # Save asset data
            if asset_data:
                asset_cache = cache_dir / f"{key}_assets.json"
                asset_api._cache.add_assets(asset_data)
                asset_api._cache.save_to_disk(asset_cache)
            
            logger.debug(f"Cached {len(class_data)} classes and {len(asset_data)} assets for {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save cache for {key}: {e}")
            return False

    def load_cache(self, key: str, task: str = "") -> CacheableData:
        """Load data from appropriate cache location."""
        try:
            # Determine cache location
            if key == "base_game":
                cache_dir = self.base_game_dir
            else:
                cache_dir = self.tasks_dir / task if task else self.tasks_dir
            
            result: CacheableData = {}
            
            # Create task-specific APIs to load data
            class_api, asset_api = self.create_apis(cache_dir)
            
            # Load class data
            class_cache = cache_dir / f"{key}_classes.json"
            if class_cache.exists():
                class_data = class_api.cache.load_from_disk(class_cache)
                result.update(cast(Dict[str, ClassData], class_data))
            
            # Load asset data
            asset_cache = cache_dir / f"{key}_assets.json"
            if asset_cache.exists():
                asset_data = asset_api._cache.load_from_disk(asset_cache)
                result.update(cast(Dict[str, Asset], asset_data))
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to load cache for {key}: {e}")
            return {}
