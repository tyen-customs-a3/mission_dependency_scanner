from pathlib import Path
from typing import Dict, Set, Any, Optional, Sequence, List, Tuple
import logging

from mission_scanner import ScanResult

from dependency_scanner.core.types import ValidationResult, EquipmentIgnoreList
from dataclasses import dataclass, field
from dependency_scanner.core.analysis.fuzzy_matcher import FuzzyClassMatcher
from dependency_scanner.core.analysis.fuzzy_config import FuzzyMatchConfig
from dependency_scanner.core.analysis.fuzzy_result import FuzzyMatchResult

logger = logging.getLogger(__name__)


@dataclass
class ScanResultAdapter:
    """Adapter for ScanResult that adds suggestion support."""
    scan_result: ScanResult
    class_suggestions: Dict[str, List[Tuple[str, float]]] = field(default_factory=dict)

class DependencyValidator:
    """Validates mission dependencies against game and mod content."""

    def __init__(self, max_workers: int = 16, ignore_patterns: Optional[Sequence[str]] = None):
        self.max_workers = max_workers
        self.ignore_list = EquipmentIgnoreList(list(ignore_patterns) if ignore_patterns else [])
        self.scan_adapters: Dict[Path, ScanResultAdapter] = {}
        self.fuzzy_matcher = FuzzyClassMatcher()  # Add fuzzy matcher instance

    def validate_content(self,
                         mission_results: Dict[Path, ScanResult],
                         game_content: Dict[str, Any],
                         task_content: Dict[str, Any]) -> Optional[Dict[Path, ValidationResult]]:

        """Validate mission content against game and task content."""
        try:
            # Reset adapters for new validation
            self.scan_adapters.clear()

            # Don't require task content
            if not game_content.get('classes'):
                logger.error("Game content is empty")
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
            if len(combined_classes) < (len(game_content.get('classes', {})) + len(task_content.get('classes', {}))):
                logger.warning(
                    f"Potential class overlap detected: {len(game_content.get('classes', {})) + len(task_content.get('classes', {})) - len(combined_classes)} "
                    f"classes may have been overwritten"
                )

            if len(combined_assets) < (len(game_content.get('assets', {})) + len(task_content.get('assets', {}))):
                logger.warning(
                    f"Potential asset overlap detected: {len(game_content.get('assets', {})) + len(task_content.get('assets', {})) - len(combined_assets)} "
                    f"assets may have been overwritten"
                )

            # Ensure we have content to validate against
            if not combined_classes and not combined_assets:
                logger.error("No content available for validation")
                return None

            logger.info(f"Validating against {len(combined_classes)} classes and {len(combined_assets)} assets")
            
            validation_results = {}
            for mission_path, scan_result in mission_results.items():
                # Don't wrap in adapter if direct usage works
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
                                 scan_result: ScanResult | ScanResultAdapter,
                                 classes: Dict[str, Any],
                                 assets: Dict[str, Any]) -> ValidationResult:
        """Validate a single mission's dependencies."""
        valid_classes: Set[str] = set()
        missing_classes: Set[str] = set()
        valid_assets: Set[str] = set()
        missing_assets: Set[str] = set()
        suggestions: Dict[str, List[Tuple[str, float]]] = {}

        self._validate_classes(scan_result, classes, valid_classes, missing_classes, suggestions)

        return ValidationResult(
            valid_assets=valid_assets,
            valid_classes=valid_classes,
            missing_assets=missing_assets,
            missing_classes=missing_classes,
            property_results={},
            class_suggestions=suggestions
        )

    def _validate_classes(self,
                          scan_result: ScanResult | ScanResultAdapter,
                          classes: Dict[str, Any],
                          valid_classes: Set[str],
                          missing_classes: Set[str],
                          suggestions: Dict[str, List[Tuple[str, float]]]) -> None:
        """Validate class dependencies."""
        # Handle both direct ScanResult and adapter
        if isinstance(scan_result, ScanResultAdapter):
            equipment = scan_result.scan_result.equipment
        else:
            equipment = scan_result.equipment

        # Get equipment names, handling both Set[str] and Dict[str, Any] types
        if isinstance(equipment, dict):
            equipment_names = equipment.keys()
        else:
            equipment_names = equipment

        logger.info(f"Starting validation of {len(equipment_names)} equipment classes")

        # Convert all class names to lowercase for case-insensitive comparison
        equipment_classes_lower = {str(class_name).lower() 
                                 for class_name in equipment_names if class_name}
        content_classes_lower = {k.lower(): k for k in classes.keys()}

        for class_name_lower in equipment_classes_lower:
            # Skip ignored equipment
            if self.ignore_list.should_ignore(class_name_lower):
                logger.debug(f"Ignoring class: '{class_name_lower}' - Matches ignore pattern")
                continue

            if class_name_lower in content_classes_lower:
                original_name = content_classes_lower[class_name_lower]
                logger.debug(f"Found valid class: '{original_name}'")
                valid_classes.add(original_name)
            else:
                logger.debug(f"Missing class: '{class_name_lower}' - Not found in available content")
                missing_classes.add(class_name_lower)
                # Generate suggestions for missing class
                fuzzy_result = self.fuzzy_matcher.find_similar_classes(
                    class_name_lower, 
                    set(content_classes_lower.keys())
                )
                if fuzzy_result.matches:  # Access matches from FuzzyMatchResult
                    suggestions[class_name_lower] = [
                        (content_classes_lower[s[0]], s[1]) for s in fuzzy_result.matches
                    ]
