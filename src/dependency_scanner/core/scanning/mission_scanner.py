from pathlib import Path
from typing import Any, Dict, Optional, List
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from mission_scanner import MissionScanner
from dependency_scanner.core.types import ScanResult

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
        if hasattr(self._scanner, 'close'):
            self._scanner.close()

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
                return self._convert_mission_result(result)
        except Exception as e:
            logger.error(f"Error scanning mission {path}: {e}")
        return None

    def _convert_mission_result(self, raw_result: Any) -> ScanResult:
        """Convert scanner result to internal format."""
        return ScanResult(
            valid_assets=set(getattr(raw_result, 'valid_assets', set())),
            valid_classes=set(getattr(raw_result, 'valid_classes', set())),
            missing_assets=set(getattr(raw_result, 'missing_assets', set())),
            missing_classes=set(getattr(raw_result, 'missing_classes', set())),
            equipment=set(getattr(raw_result, 'equipment', set())),
            property_results=getattr(raw_result, 'property_results', {}),
            class_details=self._convert_class_details(getattr(raw_result, 'classes', {}))
        )

    def _convert_class_details(self, class_data: Dict) -> Dict:
        """Convert class details to internal format."""
        return {
            name: {
                'parent': getattr(data, 'parent', 'Unknown'),
                'source_file': str(getattr(data, 'source_file', 'Unknown')),
                'properties': {
                    k: getattr(v, 'raw_value', str(v))
                    for k, v in getattr(data, 'properties', {}).items()
                }
            }
            for name, data in class_data.items()
        }
