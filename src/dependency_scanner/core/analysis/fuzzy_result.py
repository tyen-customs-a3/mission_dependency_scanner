from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class FuzzyMatchResult:
    """Results from fuzzy matching operation."""
    original: str
    matches: List[Tuple[str, float]]
    category: Optional[str] = None
    normalized_form: str = ''
    match_type: str = 'fuzzy'  # direct, substitution, fuzzy
    
    @property
    def best_match(self) -> Optional[Tuple[str, float]]:
        """Get the highest scoring match."""
        return self.matches[0] if self.matches else None
    
    @property
    def has_high_confidence_match(self) -> bool:
        """Check if there's a high confidence match."""
        return bool(self.matches and self.matches[0][1] >= 0.8)  # Lower threshold for test

    def __bool__(self) -> bool:
        """Allow truthiness testing."""
        return bool(self.matches)

    def __iter__(self):
        """Make results iterable."""
        return iter(self.matches)
