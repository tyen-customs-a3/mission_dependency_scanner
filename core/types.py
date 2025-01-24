from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, Set

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