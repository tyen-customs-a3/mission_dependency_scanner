from pathlib import Path
from typing import Dict, Set, List, Tuple, Optional
import logging

from dependency_scanner.core.types import ValidationResult
from dependency_scanner.core.analysis.fuzzy_matcher import FuzzyClassMatcher

logger = logging.getLogger(__name__)

class ClassAnalyzer:
    """Analyzes class dependencies and generates summary reports."""
    
    def __init__(self, fuzzy_matcher: Optional[FuzzyClassMatcher] = None):
        self.fuzzy_matcher = fuzzy_matcher if fuzzy_matcher is not None else FuzzyClassMatcher()
        self._processed_classes: Set[str] = set()
        self._class_suggestions: Dict[str, List[Tuple[str, float]]] = {}
        
    def analyze_results(self, validation_results: Dict[Path, ValidationResult]) -> Dict[str, Set[str]]:
        """Analyze validation results and return categorized class sets."""
        all_valid = set()
        all_missing = set()
        
        # Collect all unique class names
        for result in validation_results.values():
            all_valid.update(result.valid_classes)
            all_missing.update(result.missing_classes)
            
        # Process missing classes just once
        unprocessed_missing = all_missing - self._processed_classes
        if unprocessed_missing:
            self._find_suggestions_for_classes(unprocessed_missing, all_valid)
            self._processed_classes.update(unprocessed_missing)
            
        # Apply suggestions to all results that need them
        self._apply_suggestions_to_results(validation_results)
            
        return {
            "valid": all_valid,
            "missing": all_missing
        }
    
    def write_class_summary(self, path: Path, class_sets: Dict[str, Set[str]]) -> None:
        """Write a summary of all unique class names."""
        try:
            with path.open('w', encoding='utf-8') as f:
                f.write("=== Class Name Summary ===\n\n")
                
                # Write valid classes
                f.write("[+] Valid Classes\n")
                f.write("-" * 50 + "\n")
                for class_name in sorted(class_sets["valid"]):
                    f.write(f"{class_name}\n")
                    
                f.write(f"\nTotal Valid: {len(class_sets['valid'])}\n\n")
                
                # Write missing classes with suggestions
                f.write("[!] Missing Classes\n")
                f.write("-" * 50 + "\n")
                for class_name in sorted(class_sets["missing"]):
                    f.write(f"{class_name}\n")
                    if class_name in self._class_suggestions:
                        f.write("  Suggested replacements:\n")
                        for suggestion, score in self._class_suggestions[class_name]:
                            f.write(f"  └─ {suggestion} ({score:.2f})\n")
                    
                f.write(f"\nTotal Missing: {len(class_sets['missing'])}\n")
                
        except Exception as e:
            logger.error(f"Failed to write class summary: {e}")
    
    def _find_suggestions_for_classes(self, missing_classes: Set[str], valid_classes: Set[str]) -> None:
        """Find suggestions for missing classes only once."""
        for missing_class in missing_classes:
            suggestions = self.fuzzy_matcher.find_similar_classes(missing_class, valid_classes)
            if suggestions:
                self._class_suggestions[missing_class] = suggestions
                
    def _apply_suggestions_to_results(self, validation_results: Dict[Path, ValidationResult]) -> None:
        """Apply cached suggestions to all validation results."""
        for result in validation_results.values():
            for missing_class in result.missing_classes:
                if missing_class in self._class_suggestions:
                    result.class_suggestions[missing_class] = self._class_suggestions[missing_class]
