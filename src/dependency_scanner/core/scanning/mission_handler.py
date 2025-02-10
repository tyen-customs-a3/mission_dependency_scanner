from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Optional
import logging

from dependency_scanner.core.types import ScanResult
from mission_scanner import MissionScanner
from mission_scanner.models import ScanResult as MissionScanResult

logger = logging.getLogger(__name__)

class MissionHandler:
    """Handles mission scanning operations."""
    
    def __init__(self, max_workers: int = 16):
        self.max_workers = max_workers
        self.scanner = MissionScanner()
        self._executor = None
    
    def close(self):
        """Cleanup resources."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
    
    def scan_missions(self, missions: list[Path]) -> Dict[Path, ScanResult]:
        """Scan multiple missions in parallel."""
        if not self._executor:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
            
        results = {}
        mission_paths = []

        # First, collect all individual mission directories
        for path in missions:
            if path.is_dir():
                # Each direct subdirectory that contains mission files is treated as a separate mission
                for mission_dir in path.iterdir():
                    if mission_dir.is_dir() and self._is_mission_directory(mission_dir):
                        logger.info(f"Found mission directory: {mission_dir}")
                        mission_paths.append(mission_dir)
            elif self._is_mission_directory(path):
                logger.info(f"Found mission directory: {path}")
                mission_paths.append(path)
        
        if not mission_paths:
            logger.warning("No valid mission directories found")
            return results
            
        logger.info(f"Found {len(mission_paths)} missions to scan:")
        for path in sorted(mission_paths):
            logger.info(f"  - {path.name}")
        
        # Scan each mission directory
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._scan_single_mission, mission): mission
                for mission in mission_paths
            }
            
            for future in as_completed(futures):
                mission = futures[future]
                try:
                    if result := future.result():
                        results[mission] = result
                        logger.info(f"Completed scan of mission: {mission.name}")
                except Exception as e:
                    logger.error(f"Failed to scan mission {mission}: {e}", exc_info=True)
        
        return results

    def _is_mission_directory(self, path: Path) -> bool:
        """Check if a directory is a valid mission directory."""
        if not path.is_dir():
            return False
            
        # Check for common mission file indicators
        mission_indicators = [
            "mission.sqm",
            "description.ext",
            "init.sqf"
        ]
        
        return any((path / indicator).exists() for indicator in mission_indicators)
    
    def _scan_single_mission(self, mission_path: Path) -> Optional[ScanResult]:
        """Scan a single mission directory."""
        logger.debug(f"Scanning mission: {mission_path}")
        try:
            if result := self.scanner.scan_directory(mission_path):
                logger.debug(f"Scan result for {mission_path}: {result}")
                return self._convert_mission_result(result)
        except Exception as e:
            logger.error(f"Error scanning mission {mission_path}: {e}", exc_info=True)
        return None
    
    def _convert_mission_result(self, result: MissionScanResult) -> ScanResult:
        """Convert mission scanner result to dependency scanner result."""
        equipment = set(getattr(result, 'equipment', set()))
        logger.debug(f"Converting mission result with {len(equipment)} equipment classes")
        
        scan_result = ScanResult(
            valid_assets=set(getattr(result, 'valid_assets', set())),
            valid_classes=set(getattr(result, 'valid_classes', set())),
            missing_assets=set(getattr(result, 'missing_assets', set())),
            missing_classes=set(getattr(result, 'missing_classes', set())),
            equipment=equipment,
            property_results=getattr(result, 'property_results', {}),
            class_details={
                name: {
                    'parent': getattr(data, 'parent', 'Unknown'),
                    'source_file': str(getattr(data, 'source_file', 'Unknown')),
                    'properties': {
                        prop_name: getattr(prop, 'raw_value', str(prop))
                        for prop_name, prop in getattr(data, 'properties', {}).items()
                    }
                }
                for name, data in getattr(result, 'classes', {}).items()
            }
        )
        logger.debug(f"Converted result: {len(scan_result.equipment)} equipment, "
                    f"{len(scan_result.valid_classes)} valid, "
                    f"{len(scan_result.missing_classes)} missing")
        return scan_result
