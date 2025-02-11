from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple, Set, Dict, Any

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

@dataclass
class ScanTask:
    """Configuration for a specific scanning task"""
    name: str
    mods: list[Path]

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

@dataclass
class ScanResult:
    """Mission scan results."""
    valid_assets: Set[str] = field(default_factory=set)
    valid_classes: Set[str] = field(default_factory=set)
    missing_assets: Set[str] = field(default_factory=set)
    missing_classes: Set[str] = field(default_factory=set)
    equipment: Set[str] = field(default_factory=set)
    property_results: Dict[str, Any] = field(default_factory=dict)
    class_details: Dict[str, Any] = field(default_factory=dict)

    def sanitize(self) -> None:
        """Ensure all sets contain only strings."""
        self.valid_assets = {str(x) for x in self.valid_assets if x}
        self.valid_classes = {str(x) for x in self.valid_classes if x}
        self.missing_assets = {str(x) for x in self.missing_assets if x}
        self.missing_classes = {str(x) for x in self.missing_classes if x}
        self.equipment = {str(x) for x in self.equipment if x}

@dataclass
class ValidationResult:
    """Mission validation results."""
    valid_assets: Set[str]
    valid_classes: Set[str]
    missing_assets: Set[str]
    missing_classes: Set[str]
    property_results: Dict[str, Any]