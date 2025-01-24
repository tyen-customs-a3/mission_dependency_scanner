from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, Set, Dict

# Define categories/properties to ignore during validation
IGNORED_CATEGORIES = {
    # Unit special abilities
    "traits[]",
    "speakers[]",
    "faces[]",
    "insignias[]",
    "identities[]",
    
    # Mission/Environment settings
    "variables[]",
    "colors[]",
    "params[]",
    "sounds[]",
    "music[]",
    
    # UI/Display elements
    "controls[]",
    "textures[]",
    "fonts[]",
    "styles[]",
    
    # Script/Function names
    "functions[]",
    "scriptPaths[]",
    "eventHandlers[]",
}

class PropertyInfo(NamedTuple):
    """Information about a property found in mission files."""
    name: str
    type: str  # The property type (e.g., 'traits', 'magazines', etc.)
    value: str

class ValidationResult(NamedTuple):
    """Results of mission validation."""
    valid_assets: Set[str]
    valid_classes: Set[str]
    missing_assets: Set[str]
    missing_classes: Set[str]

@dataclass
class ScanTask:
    """Configuration for a specific scanning task"""
    name: str
    mods: list[Path]
    class_config: Path
    skip_assets: bool = False

@dataclass
class MissionClass:
    """Represents a class definition from a mission file."""
    name: str
    properties: Dict[str, list[str]]  # Property name -> list of values

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

class ValidationResult(NamedTuple):
    """Results of mission validation."""
    valid_assets: Set[str]
    valid_classes: Set[str]
    missing_assets: Set[str]
    missing_classes: Set[str]
    property_results: Dict[str, PropertyValidationResult]  # Property type -> validation results