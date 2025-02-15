from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple, Set, Dict, Any, List, Tuple
from fnmatch import fnmatch

IGNORED_CATEGORIES = {
    "traits[]",
    "speakers[]",
    "faces[]",
    "insignias[]",
    "identities[]",
    
    "variables[]",
    "colors[]",
    "params[]",
    "sounds[]",
    "music[]",
    
    "controls[]",
    "textures[]",
    "fonts[]",
    "styles[]",
    
    "functions[]",
    "scriptPaths[]",
    "eventHandlers[]",
}

DEFAULT_IGNORED_EQUIPMENT = [
    # role specific classes with wildcards
    "rm",      # Regular rifleman variants
    "ar",      # Auto rifleman variants
    "aar",     # Assistant auto rifleman
    "sh",      # Squad helper
    "tl",      # Team leader variants
    "sl",      # Squad leader variants
    "sgt",     # Sergeant variants
    "co",      # Commander variants
    "cls",     # Corpsman/medic variants
    "mmg",     # Machine gunner variants
    "ammg",    # Assistant machine gunner
    "tlmmg",   # MMG team leader
    "rm_*",    # Rifleman with specific role
    "mmg_*",   # Machine gunner with specific role
    "mat",     # AT missile variants
    "maa",     # AA missile variants
    "sierra",  # Tank
    "spotter", # Spotter variants
    "se_*",    # Special equipment
    
    "plain",   # Plain variants
    
    # Additional classes
    "*tarkov*",  # Anything containing tarkov
    "diw_armor_plates_main_plate"  # Specific plate
]

class PropertyInfo(NamedTuple):
    """Information about a property found in mission files."""
    name: str
    type: str
    value: str

class EquipmentIgnoreList:
    """Manages equipment ignore patterns with wildcard support."""
    
    def __init__(self, patterns: List[str]):
        base_patterns = DEFAULT_IGNORED_EQUIPMENT.copy()
        base_patterns.extend(patterns)
        # Filter out empty patterns and ensure they're lowercase
        self.patterns = [p.lower() for p in base_patterns if p]
        
    def should_ignore(self, equipment_name: str) -> bool:
        """Check if equipment name matches any ignore pattern."""
        if not equipment_name:  # Don't match empty strings
            return False
            
        name = equipment_name.lower()
        return any(fnmatch(name, pattern) for pattern in self.patterns)
    
    @staticmethod
    def from_config(config: List[str]) -> 'EquipmentIgnoreList':
        return EquipmentIgnoreList([p for p in (config or []) if p])  # Filter empty patterns

@dataclass
class ScanTask:
    """Scanning task configuration."""
    name: str
    data_path: List[Path]
    ignore_patterns: List[str] = field(default_factory=list)

@dataclass
class MissionClass:
    """Represents a class definition from a mission file."""
    name: str
    properties: Dict[str, list[str]]

    def has_property(self, name: str) -> bool:
        """Check if class has a specific property."""
        return name in self.properties
    
    def get_property(self, name: str) -> list[str]:
        """Get values for a property.""" 
        return self.properties.get(name, [])

@dataclass
class PropertyValidationResult:
    """Validation results for a specific property type."""
    property_type: str
    valid_values: Set[str]
    missing_values: Set[str]
    ignored_values: Set[str]

@dataclass
class ScanResult:
    """Mission scan results with added suggestions."""
    equipment: Set[str] = field(default_factory=set)
    valid_assets: Set[Path] = field(default_factory=set)
    invalid_assets: Set[Path] = field(default_factory=set)
    property_results: Dict[str, Any] = field(default_factory=dict)
    class_details: Dict[str, Any] = field(default_factory=dict)
    class_suggestions: Dict[str, List[Tuple[str, float]]] = field(default_factory=dict)

@dataclass
class ValidationResult:
    """Results of dependency validation."""
    valid_assets: Set[str]
    valid_classes: Set[str]
    missing_assets: Set[str]
    missing_classes: Set[str]
    property_results: Dict[str, Any]
    class_suggestions: Dict[str, List[Tuple[str, float]]] = field(default_factory=dict)