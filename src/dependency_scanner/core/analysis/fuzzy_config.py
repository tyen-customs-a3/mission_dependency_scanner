from dataclasses import dataclass, field
from typing import Dict, Set

@dataclass
class FuzzyMatchConfig:
    """Configuration for fuzzy matching behavior."""
    similarity_threshold: float = 0.75
    base_weight: float = 0.7
    substitution_weight: float = 0.3
    quick_match_threshold: float = 0.9
    cache_size: int = 1024
    max_suggestions: int = 3  # Add missing config parameter
    high_confidence_threshold: float = 0.9  # Add threshold for high confidence matches
    
    categories: Dict[str, Set[str]] = field(default_factory=lambda: {
        'helmet': {'helmet', 'hat', 'cap', 'boonie', 'cover'},
        'vest': {'vest', 'carrier', 'plate', 'armor'},
        'uniform': {'uniform', 'shirt', 'combat', 'clothing'},
        'weapon': {'rifle', 'gun', 'pistol', 'launcher', 'carbine'},
        'attachment': {'optic', 'scope', 'sight', 'suppressor', 'silencer', 'grip'},
    })
    
    word_substitutions: Dict[str, Set[str]] = field(default_factory=lambda: {
        'aegis': {'hat', 'helmet', 'uniform', 'vest'},
        'addon': {'add', 'equipment'},
        'nomex': {'nmx', 'nometex'},
        'simc': {'sim', 'simc_us'},
        'blk': {'black'},
        'tan': {'desert', 'sand'},
        'od': {'olive'},
        'multicam': {'mc', 'multi'},
    })
