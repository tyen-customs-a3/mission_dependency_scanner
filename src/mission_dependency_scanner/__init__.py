"""Mission dependency scanning functionality."""

from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import logging

from asset_scanner import AssetAPI
from ini_class_parser import ClassHierarchyAPI
from mission_scanner import Scanner as MissionScanner

@dataclass
class ScanResult:
    missing_assets: Set[str]
    missing_classes: Set[str]
    unknown_references: Set[str]
    valid_assets: Set[str]
    valid_classes: Set[str]

class DependencyScanner:
    def __init__(self, cache_dir: Path = Path("cache")):
        self.asset_api = AssetAPI(cache_dir)
        self.class_api = ClassHierarchyAPI()
        self.mission_scanner = MissionScanner()
        self.asset_db: Set[str] = set()
        self.class_db: Dict[str, Set[str]] = {}
        
    def build_asset_database(self, mod_paths: List[Path]) -> None:
        """Scan mod directories to build asset database."""
        for path in mod_paths:
            assets = self.asset_api.scan_directory(path)
            self.asset_db.update(self.asset_api.get_all_assets())

    def build_class_database(self, config_paths: List[Path]) -> None:
        """Parse config files to build class database."""
        for path in config_paths:
            self.class_api.parse_config(path)
            for category in self.class_api.get_available_categories():
                self.class_db[category] = set(
                    self.class_api.get_all_classes(category)
                )

    def validate_mission(self, mission_path: Path) -> ScanResult:
        """Scan mission and validate all dependencies exist."""
        # Scan mission files
        scan_results = self.mission_scanner.scan_directory(mission_path)
        
        missing_assets = set()
        missing_classes = set()
        unknown_refs = set()
        valid_assets = set()
        valid_classes = set()

        # Check each reference
        for file_result in scan_results:
            for ref in file_result.equipment:
                # Try as asset path
                if ref in self.asset_db:
                    valid_assets.add(ref)
                    continue
                    
                # Try as class name in each category
                found = False
                for category, classes in self.class_db.items():
                    if ref in classes:
                        valid_classes.add(ref)
                        found = True
                        break
                        
                if not found:
                    if ref.endswith(('.paa', '.p3d', '.wss')):
                        missing_assets.add(ref)
                    else:
                        missing_classes.add(ref)

        return ScanResult(
            missing_assets=missing_assets,
            missing_classes=missing_classes,
            unknown_references=unknown_refs,
            valid_assets=valid_assets,
            valid_classes=valid_classes
        )
