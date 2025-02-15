import pytest
from mission_scanner import ScanResult

@pytest.fixture
def empty_scan_result():
    """Create an empty scan result."""
    return ScanResult()

@pytest.fixture
def sample_scan_result():
    """Create a scan result with sample data."""
    result = ScanResult()
    result.equipment = {
        "rm_test_item",
        "ace_medical_bandage",
        "tarkov_weapon",
        "regular_item",
        "test_ignore_this"
    }
    return result
