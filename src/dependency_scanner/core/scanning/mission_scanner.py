from pathlib import Path
from typing import Dict, Optional, List
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from mission_scanner import MissionScanner, ScanResult

logger = logging.getLogger(__name__)

class MissionScanningService:
    """Handles all mission scanning operations."""
    
    def __init__(self, max_workers: int = 16):
        self.max_workers = max_workers
        self._scanner = MissionScanner()
        self._executor: Optional[ThreadPoolExecutor] = None
        
    def scan_missions(self, mission_paths: List[Path]) -> Dict[Path, ScanResult]:
        """Scan multiple missions in parallel."""
        valid_paths = self._validate_mission_paths(mission_paths)
        if not valid_paths:
            logger.error("No valid mission paths found")
            return {}
            
        results = {}
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        try:
            futures = {
                self._executor.submit(self._scan_single_mission, path): path
                for path in valid_paths
            }
            
            for future in as_completed(futures):
                path = futures[future]
                try:
                    if result := future.result():
                        results[path] = result
                        logger.info(f"Completed scan of mission: {path.name}")
                except Exception as e:
                    logger.error(f"Failed to scan mission {path}: {e}")
                    
            return results
        finally:
            self._executor.shutdown(wait=False)
            self._executor = None

    def close(self) -> None:
        """Clean up resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

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

    def _scan_single_mission(self, path: Path) -> Optional[ScanResult]:
        """Scan a single mission directory."""
        try:
            if result := self._scanner.scan_directory(path):
                return result
        except Exception as e:
            logger.error(f"Error scanning mission {path}: {e}")
        return None
