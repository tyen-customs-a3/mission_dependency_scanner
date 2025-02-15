from pathlib import Path
from typing import Dict, Optional, List
import logging
from concurrent.futures import ThreadPoolExecutor
from mission_scanner import MissionScannerAPI, ScanResult, MissionScannerAPIConfig

logger = logging.getLogger(__name__)

class MissionScanningService:
    """Handles all mission scanning operations."""
    
    def __init__(self, max_workers: int = 30, cache_dir: Optional[Path] = None):
        self.max_workers = max_workers
        self._executor: Optional[ThreadPoolExecutor] = None
        
        # Ensure proper cache directory structure
        if cache_dir:
            mission_cache_dir = cache_dir / "missions"
        else:
            mission_cache_dir = Path(".cache/missions")
            
        mission_cache_dir.mkdir(parents=True, exist_ok=True)
        
        config = MissionScannerAPIConfig(
            max_workers=max_workers,
            cache_max_size=1_000_000,  # 1M entries
        )
        self._scanner = MissionScannerAPI(
            cache_dir=mission_cache_dir,
            config=config
        )
        
    def scan_missions(self, mission_paths: List[Path]) -> Dict[Path, ScanResult]:
        """Scan multiple missions using built-in caching."""
        valid_paths = self._validate_mission_paths(mission_paths)
        if not valid_paths:
            logger.error("No valid mission paths found")
            return {}
            
        results = {}
        for path in valid_paths:
            try:
                # MissionScannerAPI handles caching internally
                if result := self._scanner.scan_directory(path):
                    results[path] = result
                    logger.info(f"Completed scan of mission: {path.name}")
                    logger.info(f"Classes: {len(result.classes)}")
                    logger.info(f"Equipment: {len(result.equipment)}")
                    
            except Exception as e:
                logger.error(f"Failed to scan mission {path}: {e}")
                
        return results

    def close(self) -> None:
        """Clean up resources."""
        if hasattr(self, '_scanner'):
            self._scanner.cleanup()

    @staticmethod
    def is_mission_directory(path: Path) -> bool:
        """Check if directory contains mission files. Made static for reuse."""
        if not path.is_dir():
            return False
            
        indicators = ["mission.sqm", "description.ext", "init.sqf"]
        return any((path / indicator).exists() for indicator in indicators)

    def _validate_mission_paths(self, paths: List[Path]) -> List[Path]:
        """Filter and validate mission paths."""
        valid_paths = []
        for path in paths:
            if self.is_mission_directory(path):
                valid_paths.append(path.resolve())
            elif path.is_dir():
                valid_paths.extend(
                    p.resolve() for p in path.iterdir()
                    if p.is_dir() and self.is_mission_directory(p)
                )
        return valid_paths
