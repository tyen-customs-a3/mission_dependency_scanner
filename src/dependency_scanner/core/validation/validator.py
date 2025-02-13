from pathlib import Path
from typing import Dict, Set, Any, Optional
import logging

from mission_scanner import ScanResult

from dependency_scanner.core.types import ValidationResult

logger = logging.getLogger(__name__)


class DependencyValidator:
    """Validates mission dependencies against game and mod content."""

    def __init__(self, max_workers: int = 16):
        self.max_workers = max_workers

    def validate_content(self,
                         mission_results: Dict[Path, ScanResult],
                         game_content: Dict[str, Any],
                         task_content: Dict[str, Any]) -> Optional[Dict[Path, ValidationResult]]:

        """Validate mission content against game and task content."""
        try:
            # Get initial lengths for validation
            game_class_count = len(game_content.get('classes', {}))
            game_asset_count = len(game_content.get('assets', {}))
            task_class_count = len(task_content.get('classes', {}))
            task_asset_count = len(task_content.get('assets', {}))

            # Make sure the content is more than just empty dictionaries
            if not game_class_count and not game_asset_count:
                logger.error("Game content is empty")
                return None
            
            if not task_class_count and not task_asset_count:
                logger.error("Task content is empty")
                return None

            # Merge game and task content
            combined_classes = {
                **game_content.get('classes', {}),
                **task_content.get('classes', {})
            }
            
            combined_assets = {
                **game_content.get('assets', {}),
                **task_content.get('assets', {})
            }

            # Verify merge was successful
            if len(combined_classes) < (game_class_count + task_class_count):
                logger.warning(
                    f"Potential class overlap detected: {game_class_count + task_class_count - len(combined_classes)} "
                    f"classes may have been overwritten"
                )

            if len(combined_assets) < (game_asset_count + task_asset_count):
                logger.warning(
                    f"Potential asset overlap detected: {game_asset_count + task_asset_count - len(combined_assets)} "
                    f"assets may have been overwritten"
                )

            # Ensure we have content to validate against
            if not combined_classes and not combined_assets:
                logger.error("No content available for validation")
                return None

            logger.info(f"Validating against {len(combined_classes)} classes and {len(combined_assets)} assets")
            
            validation_results = {}
            for mission_path, scan_result in mission_results.items():
                validation_results[mission_path] = self._validate_single_mission(
                    scan_result,
                    combined_classes,
                    combined_assets
                )
                
            return validation_results
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return None

    def _validate_single_mission(self,
                                 scan_result: ScanResult,
                                 classes: Dict[str, Any],
                                 assets: Dict[str, Any]) -> ValidationResult:
        """Validate a single mission's dependencies."""
        valid_classes: Set[str] = set()
        missing_classes: Set[str] = set()
        valid_assets: Set[str] = set()
        missing_assets: Set[str] = set()

        self._validate_classes(scan_result, classes, valid_classes, missing_classes)

        # TODO: Implement asset validation
        # self._validate_assets(scan_result, assets, valid_assets, missing_assets)

        return ValidationResult(
            valid_assets=valid_assets,
            valid_classes=valid_classes,
            missing_assets=missing_assets,
            missing_classes=missing_classes,
            property_results={}
        )

    def _validate_classes(self,
                          scan_result: ScanResult,
                          classes: Dict[str, Any],
                          valid_classes: Set[str],
                          missing_classes: Set[str]) -> None:
        """Validate class dependencies."""
        logger.info(f"Starting validation of {len(scan_result.equipment)} equipment classes")

        # Convert all class names to lowercase for case-insensitive comparison
        equipment_classes_lower = {str(class_name).lower() for class_name in scan_result.equipment if class_name}
        content_classes_lower = {k.lower(): k for k in classes.keys()}

        for class_name_lower in equipment_classes_lower:
            
            if class_name_lower in content_classes_lower:
                original_name = content_classes_lower[class_name_lower]
                logger.debug(f"Found valid class: '{original_name}'")
                valid_classes.add(original_name)
            else:
                logger.debug(f"Missing class: '{class_name_lower}' - Not found in available content")
                missing_classes.add(class_name_lower)
