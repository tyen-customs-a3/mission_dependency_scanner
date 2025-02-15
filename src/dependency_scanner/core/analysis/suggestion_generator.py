from pathlib import Path
from typing import Dict, Set, List, Tuple, Optional
import logging
from dataclasses import dataclass

from dependency_scanner.core.analysis.fuzzy_matcher import FuzzyClassMatcher
from dependency_scanner.core.analysis.fuzzy_config import FuzzyMatchConfig

logger = logging.getLogger(__name__)

@dataclass
class SuggestionReport:
    """Contains class suggestions for all missing equipment."""
    suggestions: Dict[str, List[Tuple[str, float]]]
    categories: Dict[str, str]

class SuggestionGenerator:
    """Generates suggestions for missing classes after all validations are complete."""
    
    def __init__(self, max_workers: Optional[int] = None):
        config = FuzzyMatchConfig()
        self.fuzzy_matcher = FuzzyClassMatcher(config=config)
        
    def generate_suggestions(self, 
                           all_missing_classes: Set[str],
                           available_classes: Set[str]) -> SuggestionReport:
        """Generate suggestions for all missing classes at once."""
        suggestions: Dict[str, List[Tuple[str, float]]] = {}
        categories: Dict[str, str] = {}
        
        # Convert available classes to lowercase for matching
        available_lower = {cls.lower(): cls for cls in available_classes}
        
        # Process all missing classes in parallel
        batch_results = self.fuzzy_matcher.find_similar_classes_batch(
            list(all_missing_classes),
            set(available_lower.keys())
        )
        
        # Process results and categorize
        for missing_class, result in batch_results.items():
            if result.matches:  # Access matches from FuzzyMatchResult
                if result.category:  # Access category from FuzzyMatchResult
                    categories[missing_class] = result.category
                
                suggestions[missing_class] = result.matches
                
                logger.info(f"Suggestions for '{missing_class}' [{result.category or 'Unknown'}]:")
                for cls, score in result.matches:
                    logger.info(f"  - {available_lower[cls]} (similarity: {score:.2f})")
                    
        return SuggestionReport(suggestions=suggestions, categories=categories)

    def write_suggestion_report(self, 
                              report_dir: Path,
                              task_name: str,
                              suggestions: SuggestionReport) -> None:
        """Write suggestions to a separate report file."""
        try:
            report_path = report_dir / f"{task_name}_suggestions.json"
            with report_path.open('w') as f:
                import json
                json.dump({
                    'suggestions': suggestions.suggestions,
                    'categories': suggestions.categories
                }, f, indent=2)
                
            logger.info(f"Wrote suggestion report to {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to write suggestion report: {e}")
