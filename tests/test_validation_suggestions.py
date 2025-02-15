import pytest
from pathlib import Path
from typing import Dict

from dependency_scanner.core.validation.validator import DependencyValidator, ScanResultAdapter

# Mock ScanResult since we can't modify the original class from mission_scanner
class MockScanResult:
    """Mock version of ScanResult for testing."""
    def __init__(self):
        self.equipment: Dict[str, str] = {}  # Matches mission_scanner's type
    
    def add_equipment(self, equipment_list: list[str]) -> None:
        """Add equipment in the format mission_scanner expects."""
        self.equipment.update({name: "mock_type" for name in equipment_list})

@pytest.fixture
def validator():
    return DependencyValidator(max_workers=1)

@pytest.fixture
def sample_mission_result():
    result = MockScanResult()
    result.add_equipment([
        'aegis_boonie_blk',
        'simc_addon_nomex_long_tan',
        'existing_class'
    ])
    return {Path('test_mission'): result}

@pytest.fixture
def sample_game_content():
    return {
        'classes': {
            'hat_boonie_black': {},
            'simc_addon_nmx_long_tan': {},
            'existing_class': {}
        },
        'assets': {}
    }

def test_validation_with_suggestions(validator, sample_mission_result, sample_game_content):
    results = validator.validate_content(
        sample_mission_result,
        sample_game_content,
        {'classes': {}, 'assets': {}}
    )
    
    assert results is not None
    mission_result = results[Path('test_mission')]
    
    # Check valid classes
    assert 'existing_class' in mission_result.valid_classes
    
    # Check missing classes have suggestions
    assert 'aegis_boonie_blk' in mission_result.missing_classes
    assert 'simc_addon_nomex_long_tan' in mission_result.missing_classes
    
    # Verify suggestions were generated
    assert mission_result.class_suggestions
    assert any('hat_boonie_black' in sugg[0] 
              for sugg in mission_result.class_suggestions.get('aegis_boonie_blk', []))
    assert any('simc_addon_nmx_long_tan' in sugg[0] 
              for sugg in mission_result.class_suggestions.get('simc_addon_nomex_long_tan', []))

def test_validation_result_adapter(validator):
    # Test that adapter properly stores suggestions
    scan_result = MockScanResult()
    scan_result.add_equipment(['test_class'])
    
    adapter = ScanResultAdapter(scan_result)
    adapter.class_suggestions['test_class'] = [('suggested_class', 0.8)]
    
    assert 'test_class' in adapter.class_suggestions
    assert adapter.class_suggestions['test_class'][0][0] == 'suggested_class'
    assert adapter.class_suggestions['test_class'][0][1] == 0.8
