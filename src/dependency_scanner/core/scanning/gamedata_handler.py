from pathlib import Path
from typing import Dict, Optional, Any, List
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from class_scanner.api import API as ClassAPI
from class_scanner.models import ClassData
from asset_scanner import AssetAPI
from dependency_scanner.core.utils import get_cache_key, save_cache, load_cache

logger = logging.getLogger(__name__)

class GameDataHandler:
    """Handles mod content scanning operations."""
    
    def __init__(self, max_workers: int = 16):
        self.max_workers = max_workers
        self.class_api = None
        self.asset_api = None
        self._class_cache = {}
        self._asset_cache = {}
        self._is_scanned = False
        self.cache_dir = None
        self._pending_cache = {}
        self._executor = None
    
    def initialize(self, cache_dir: Path):
        """Initialize scanners."""
        self.cache_dir = cache_dir / "gamedata"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if not self.asset_api:
            self.asset_api = AssetAPI(cache_dir=cache_dir / "assets")
        if not self.class_api:
            self.class_api = ClassAPI()
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
    
    def close(self):
        """Cleanup resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
    
    def scan_mod_content(self, mod_paths: list[Path]) -> Dict[str, ClassData]:
        """Scan mod directories for classes and assets once."""
        if not self.asset_api or not self.class_api:
            raise RuntimeError("ModHandler not initialized")
        
        is_game_content = len(mod_paths) == 1 and mod_paths[0].name.lower() == "arma 3"
        cache_key = None
        
        if is_game_content:
            cache_key = get_cache_key(mod_paths[0])
            logger.info(f"Processing game content with cache key: {cache_key}")
            
            # Try loading from cache first
            cached_data = load_cache(self.cache_dir, cache_key)
            if cached_data:
                logger.info(f"Using cached game data ({len(cached_data)} classes)")
                self._class_cache.update(cached_data)
                self._is_scanned = True
                return cached_data
            else:
                logger.info("No game data cache found, performing full scan...")
        
        # Perform scanning
        class_data = self._scan_mod_content(mod_paths)
        
        # Cache game content immediately after scanning
        if is_game_content and cache_key:
            logger.info(f"Writing game data cache ({len(class_data)} classes)...")
            if save_cache(self.cache_dir, cache_key, class_data):
                logger.info("Game data cache written successfully")
            else:
                logger.error("Failed to write game data cache!")

        return class_data
    
    def _scan_mod_content(self, mod_paths: list[Path]) -> Dict[str, ClassData]:
        """Internal method to perform actual scanning."""
        logger.info("Starting content scan...")
        class_data: Dict[str, ClassData] = {}
        
        all_pbos = []
        for mod_path in mod_paths:
            if not mod_path.exists():
                logger.warning(f"Mod path does not exist: {mod_path}")
                continue
                
            if mod_path.is_file() and mod_path.suffix.lower() == '.pbo':
                all_pbos.append(mod_path)
            else:
                all_pbos.extend(mod_path.rglob('*.pbo'))
        
        if not all_pbos:
            logger.warning("No PBOs found in mod paths")
            return class_data
            
        logger.info(f"Starting parallel scan of {len(all_pbos)} PBOs...")
        class_data = self._scan_pbos_parallel(all_pbos)
        
        assets_before = len(self.asset_api.get_all_assets())
        for mod_path in mod_paths:
            try:
                if mod_path.exists():
                    scan_result = self.asset_api.scan(mod_path)
                    if scan_result:
                        logger.info(f"Found {len(scan_result.assets)} assets in {mod_path.name}")
            except Exception as e:
                logger.error(f"Failed to scan assets in {mod_path}: {e}")
        
        self._class_cache = class_data  # Update in-memory cache
        self._asset_cache = {
            asset.path: asset 
            for asset in self.asset_api.get_all_assets()
        }
        
        # Log detailed results
        logger.info(f"Scan complete for {len(mod_paths)} paths:")
        logger.info(f"- Total PBOs processed: {len(all_pbos)}")
        logger.info(f"- Total classes found: {len(class_data)}")
        logger.info(f"- Total assets in cache: {len(self._asset_cache)}")
        
        if len(mod_paths) == 1:
            if cache_key := get_cache_key(mod_paths[0]):
                self._pending_cache[cache_key] = class_data
        
        self._write_pending_caches()
        
        self._is_scanned = True
        return class_data
    
    def _write_pending_caches(self):
        """Write all pending cache entries to disk."""
        if not self._pending_cache:
            return
            
        logger.info(f"Writing {len(self._pending_cache)} cache entries to disk...")
        for key, data in self._pending_cache.items():
            if save_cache(self.cache_dir, key, data):
                logger.info(f"Cached data for key: {key}")
            else:
                logger.warning(f"Failed to cache data for key: {key}")
        
        self._pending_cache.clear()

    def get_cached_class(self, class_name: str) -> Optional[ClassData]:
        """Get class from cache."""
        return self._class_cache.get(class_name)
    
    def get_cached_asset(self, asset_path: str) -> Optional[Any]:
        """Get asset from cache."""
        return self._asset_cache.get(Path(asset_path))

    def _scan_pbos_parallel(self, pbos: List[Path]) -> Dict[str, ClassData]:
        """Scan multiple PBOs in parallel and return combined results."""
        if not self._executor:
            raise RuntimeError("GameDataHandler not initialized")
            
        combined_results: Dict[str, ClassData] = {}
        future_to_pbo = {
            self._executor.submit(self._scan_single_pbo_threaded, pbo): pbo 
            for pbo in pbos
        }
        
        for future in as_completed(future_to_pbo):
            pbo = future_to_pbo[future]
            try:
                if result := future.result():
                    new_class_count = len(result)
                    logger.info(f"PBO scan complete: {pbo.name} - Found {new_class_count} classes")
                    combined_results.update(result)
            except Exception as e:
                logger.error(f"Failed to scan PBO {pbo}: {e}")
                
        return combined_results

    def _scan_single_pbo_threaded(self, pbo_path: Path) -> Dict[str, ClassData]:
        """Thread-safe version of PBO scanning that returns results instead of updating shared dict."""
        try:
            logger.debug(f"Scanning PBO: {pbo_path.name}")
            if result := self.class_api.scan_pbo(pbo_path):
                return result.classes
        except Exception as e:
            logger.error(f"Failed to scan PBO {pbo_path}: {e}")
        return {}
