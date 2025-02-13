from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple, Set, Dict, Any, List


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

class PropertyInfo(NamedTuple):
    """Information about a property found in mission files."""
    name: str
    type: str
    value: str

@dataclass
class ScanTask:
    """Scanning task configuration."""
    name: str
    data_path: List[Path]

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
    """Mission scan results, matching asset_scanner model structure."""
    equipment: Set[str] = field(default_factory=set)
    valid_assets: Set[Path] = field(default_factory=set)
    invalid_assets: Set[Path] = field(default_factory=set)
    property_results: Dict[str, Any] = field(default_factory=dict)
    class_details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationResult:
    """Results of dependency validation."""
    valid_assets: Set[str]
    valid_classes: Set[str]
    missing_assets: Set[str]
    missing_classes: Set[str]
    property_results: Dict[str, Any]