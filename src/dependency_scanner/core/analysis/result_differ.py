from pathlib import Path
from typing import Dict
import logging

from dependency_scanner.core.types import ValidationResult

logger = logging.getLogger(__name__)

class ResultDiffer:
    """Handles differencing between multiple task validation results."""

    @staticmethod
    def difference_results(base_results: Dict[Path, ValidationResult],
                         compare_results: Dict[Path, ValidationResult]) -> Dict[Path, ValidationResult]:
        """Remove missing dependencies from compare_results that also exist in base_results."""
        differenced_results = {}

        for mission_path, compare_result in compare_results.items():
            base_result = base_results.get(mission_path)
            if not base_result:
                # If mission doesn't exist in base, keep original results
                differenced_results[mission_path] = compare_result
                continue

            # Remove common missing classes/assets
            new_missing_classes = compare_result.missing_classes - base_result.missing_classes
            new_missing_assets = compare_result.missing_assets - base_result.missing_assets

            differenced_results[mission_path] = ValidationResult(
                valid_assets=compare_result.valid_assets,
                valid_classes=compare_result.valid_classes,
                missing_assets=new_missing_assets,
                missing_classes=new_missing_classes,
                property_results=compare_result.property_results
            )

        return differenced_results
