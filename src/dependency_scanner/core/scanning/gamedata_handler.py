from pathlib import Path
from typing import Dict, Optional, Any, List, Set, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib

from class_scanner.api import ClassAPI
from class_scanner.models import ClassData
from asset_scanner import AssetAPI, Asset
from asset_scanner.config import APIConfig

logger = logging.getLogger(__name__)

@dataclass
class ScanStats:
    """Statistics for scan operations."""
    pbo_count: int = 0
    class_count: int = 0
    asset_count: int = 0
    failed_pbos: int = 0

class GameDataHandler:
    """Handles mod content scanning operations."""
    
    def __init__(self, cache_dir: Path, max_workers: int = 16):
        self.cache_dir = cache_dir
        self.max_workers = max_workers
        
        # Create cache directories
        self.class_cache_dir = cache_dir / "classes"
        self.asset_cache_dir = cache_dir / "assets"
        self.class_cache_dir.mkdir(parents=True, exist_ok=True)
        self.asset_cache_dir.mkdir(parents=True, exist_ok=True)
        
    def scan_game_content(self, game_path: Path) -> Optional[Dict[str, Any]]:
        """Scan content from a game directory."""

        # Generate cache paths using @folder name
        class_cache, asset_cache = self._get_cache_paths(game_path)
        
        cached_content = self._load_from_cache(class_cache, asset_cache, game_path)
        # Print cache paths for debugging
        logger.info(f"Class cache: {class_cache}")
        logger.info(f"Asset cache: {asset_cache}")
        
        combined_classes = {}
        combined_assets = {}

        if cached_content is not None:
            logger.info(f"Using cached content for {game_path.name}")
            classes, assets = cached_content
            combined_classes.update(classes)
            combined_assets.update(assets)
        else:
            logger.info(f"Starting parallel scan of {game_path.name}")
            scan_results = self._parallel_scan_mod(game_path, class_cache, asset_cache)
            if scan_results:
                combined_classes.update(scan_results.get('classes', {}))
                combined_assets.update(scan_results.get('assets', {}))
        
        return {
            'classes': combined_classes,
            'assets': combined_assets
        }
        
    def scan_mod_content(self, mod_paths: List[Path]) -> Optional[Dict[str, Any]]:
        """Scan mod content and return combined results."""
        try:
            combined_classes = {}
            combined_assets = {}
            
            for mod_path in mod_paths:
                if not mod_path.exists():
                    logger.warning(f"Mod path does not exist: {mod_path}")
                    continue
                
                # Get all @-prefixed folders
                mod_folders = self._get_mod_folders(mod_path)
                if not mod_folders:
                    logger.warning(f"No @-prefixed folders found in: {mod_path}")
                    continue

                for folder in mod_folders:
                    # Generate cache paths using @folder name
                    class_cache, asset_cache = self._get_cache_paths(folder)
                    
                    logger.info(f"Class cache: {class_cache}")
                    logger.info(f"Asset cache: {asset_cache}")
                    
                    cached_content = self._load_from_cache(class_cache, asset_cache, folder)
                    
                    if cached_content:
                        logger.info(f"Using cached content for {folder.name}")
                        classes, assets = cached_content
                        combined_classes.update(classes)
                        combined_assets.update(assets)
                        continue
                    
                    logger.info(f"Starting parallel scan of {folder.name}")
                    scan_results = self._parallel_scan_mod(folder, class_cache, asset_cache)
                    if scan_results:
                        combined_classes.update(scan_results.get('classes', {}))
                        combined_assets.update(scan_results.get('assets', {}))
                
            return {
                'classes': combined_classes,
                'assets': combined_assets
            }
            
        except Exception as e:
            logger.error(f"Failed to scan mods: {e}")
            return None

    def _parallel_scan_mod(self, 
                          mod_path: Path, 
                          class_cache: Path,
                          asset_cache: Path) -> Optional[Dict[str, Any]]:
        """Perform parallel scanning of a mod directory."""
        try:
            # Initialize scanners with direct cache files
            class_scanner = ClassAPI(cache_file=class_cache)
            asset_scanner = AssetAPI(APIConfig(
                cache_file=asset_cache,
                max_workers=self.max_workers
            ))
            
            # Collect all PBO files
            pbo_files = list(mod_path.rglob('*.pbo'))
            if not pbo_files:
                logger.warning(f"No PBO files found in {mod_path}")
                return None
                
            # Scan PBOs in parallel
            stats = ScanStats()
            classes: Dict[str, ClassData] = {}
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_pbo = {
                    executor.submit(self._scan_pbo_for_classes, pbo, class_scanner): pbo
                    for pbo in pbo_files
                }
                
                # Process results as they complete
                for future in as_completed(future_to_pbo):
                    pbo = future_to_pbo[future]
                    try:
                        if result := future.result():
                            stats.pbo_count += 1
                            stats.class_count += len(result)
                            classes.update(result)
                            logger.debug(f"Processed PBO: {pbo.name} - Found {len(result)} classes")
                        else:
                            stats.failed_pbos += 1
                            logger.warning(f"Failed to process PBO: {pbo.name}")
                    except Exception as e:
                        stats.failed_pbos += 1
                        logger.error(f"Error processing PBO {pbo}: {e}")
            
            # Save class cache after scanning
            class_scanner.save_cache()
            
            # Scan for assets
            assets = self._scan_folder_for_assets(mod_path, asset_scanner)
            stats.asset_count = len(assets)
            
            # Log final statistics
            logger.info(f"Scan complete for {mod_path.name}:")
            logger.info(f"- Processed PBOs: {stats.pbo_count} (Failed: {stats.failed_pbos})")
            logger.info(f"- Total classes found: {stats.class_count}")
            logger.info(f"- Total assets found: {stats.asset_count}")
            
            return {
                'classes': classes,
                'assets': {str(a.path): a for a in assets}
            }
            
        except Exception as e:
            logger.error(f"Failed parallel scan of {mod_path}: {e}")
            return None

    def _scan_pbo_for_classes(self, pbo_path: Path, scanner: ClassAPI) -> Optional[Dict[str, ClassData]]:
        """Scan a single PBO file."""
        try:
            if result := scanner.scan(pbo_path):
                return dict(result.classes)
        except Exception as e:
            logger.error(f"Failed to scan PBO {pbo_path}: {e}")
        return None

    def _scan_folder_for_assets(self, mod_path: Path, scanner: AssetAPI) -> Set[Asset]:
        """Scan for assets in mod directory."""
        try:
            if result := scanner.scan(mod_path):
                scanner.save_cache()
                return result.assets
        except Exception as e:
            logger.error(f"Failed to scan assets in {mod_path}: {e}")
        return set()

    def _get_content_hash(self, folder_path: Path) -> str:
        """Calculate hash based on folder structure and file sizes."""
        try:
            # Get all files recursively
            pbo_files = list(folder_path.rglob('*.pbo'))
            if not pbo_files:
                return ""
                
            # Sort for consistent hashing
            pbo_files.sort()
            
            # Combine path and size information
            content_info = [f"{p.relative_to(folder_path)}:{p.stat().st_size}" 
                          for p in pbo_files]
            
            # Create hash of all paths and sizes
            return hashlib.blake2b(
                "|".join(content_info).encode(), 
                digest_size=16
            ).hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to calculate content hash for {folder_path}: {e}")
            return ""

    def _get_cache_paths(self, folder_path: Path) -> Tuple[Path, Path]:
        """Generate cache paths using content-based hash."""
        content_hash = self._get_content_hash(folder_path)
        base_name = f"{folder_path.name}_{content_hash}"
        return (
            self.class_cache_dir / f"{base_name}_classes.json",
            self.asset_cache_dir / f"{base_name}_assets.json"
        )

    def _load_from_cache(self, 
                        class_cache: Path, 
                        asset_cache: Path,
                        mod_path: Path) -> Optional[Tuple[Dict[str, ClassData], Dict[str, Asset]]]:
        """Try to load content from existing cache files."""
        try:
            # Check if both cache files exist
            if not (class_cache.exists() and asset_cache.exists()):
                return None
                
            # Load caches
            class_scanner = ClassAPI(cache_file=class_cache)
            if not class_scanner.cache.is_valid():
                return None
                
            asset_scanner = AssetAPI(APIConfig(cache_file=asset_cache))
            if not asset_scanner.load_cache():
                return None
                
            classes = class_scanner.cache.get_all_classes()
            assets = {str(a.path): a for a in asset_scanner.get_all_assets()}
            
            return classes, assets
            
        except Exception as e:
            logger.warning(f"Failed to load cache for {mod_path.name}: {e}")
            return None
        
    def _get_mod_folders(self, mod_path: Path) -> List[Path]:
        """Get all immediate @-prefixed folders within the mod path."""
        return [p for p in mod_path.iterdir() 
                if p.is_dir() and p.name.startswith('@')]

    def close(self) -> None:
        """Cleanup resources."""
        pass  # APIs handle their own cleanup
