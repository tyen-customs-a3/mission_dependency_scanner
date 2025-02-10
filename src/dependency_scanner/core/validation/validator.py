from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict
import logging

from dependency_scanner.core.types import ValidationResult, ScanResult
from class_scanner.models import ClassData
from asset_scanner import AssetAPI

logger = logging.getLogger(__name__)

class DependencyValidator:
    """Validates mission dependencies against available content."""
    
    def __init__(self, asset_api: AssetAPI, max_workers: int = 16):
        self.asset_api = asset_api
        self.max_workers = max_workers
    
    def validate_missions(self, 
                         mission_results: Dict[Path, ScanResult],
                         class_data: Dict[str, ClassData]) -> Dict[Path, ValidationResult]:
        """Validate multiple missions in parallel."""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._validate_single_mission, 
                    path, result, class_data
                ): path
                for path, result in mission_results.items()
            }
            
            for future in as_completed(futures):
                mission_path = futures[future]
                try:
                    if result := future.result():
                        results[mission_path] = result
                except Exception as e:
                    logger.error(f"Failed to validate mission {mission_path}: {e}")
        
        return results
    
    def _validate_single_mission(self,
                               mission_path: Path,
                               scan_result: ScanResult,
                               class_data: Dict[str, ClassData]) -> ValidationResult:
        """Validate a single mission's dependencies using cached data."""
        valid_classes = set()
        missing_classes = set()
        valid_assets = set()
        missing_assets = set()
        
        # Use cached class data
        for class_name in scan_result.equipment:
            if not class_name:
                continue
                
            if class_info := class_data.get(str(class_name)):
                valid_classes.add(class_name)
            else:
                missing_classes.add(class_name)
        
        # Use cached asset data
        for asset_path in scan_result.valid_assets:
            if self.asset_api.get_cached_asset(asset_path):
                valid_assets.add(str(asset_path))
            else:
                missing_assets.add(asset_path)
        
        return ValidationResult(
            valid_assets=valid_assets,
            valid_classes=valid_classes,
            missing_assets=missing_assets,
            missing_classes=missing_classes,
            property_results={}
        )
    
    def _validate_classes(self, scan_result: ScanResult, 
                         class_data: Dict[str, ClassData],
                         valid_classes: set, missing_classes: set):
        """Validate class dependencies."""
        logger.debug(f"Validating {len(scan_result.equipment)} equipment classes")
        
        for class_name in scan_result.equipment:
            if not class_name:
                continue
                
            if class_info := class_data.get(str(class_name)):
                if class_name in scan_result.class_details:
                    expected_parent = scan_result.class_details[class_name].get('parent')
                    if expected_parent and expected_parent != class_info.parent:
                        logger.debug(f"Class {class_name} has wrong parent: expected {expected_parent}, got {class_info.parent}")
                        missing_classes.add(class_name)
                        continue
                logger.debug(f"Found valid class: {class_name}")
                valid_classes.add(class_name)
            else:
                logger.debug(f"Missing class: {class_name}")
                missing_classes.add(class_name)
    
    def _validate_assets(self, scan_result: ScanResult,
                        valid_assets: set, missing_assets: set):
        """Validate asset dependencies."""
        for asset_path in scan_result.valid_assets:
            if asset := self.asset_api.get_asset(asset_path):
                valid_assets.add(str(asset.path))
            else:
                missing_assets.add(asset_path)
