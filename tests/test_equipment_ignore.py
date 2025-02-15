from dependency_scanner.core.types import EquipmentIgnoreList
from dependency_scanner.core.validation.validator import DependencyValidator
from mission_scanner import ScanResult


def test_default_ignored_equipment():
    """Test that default ignore patterns work."""
    ignore_list = EquipmentIgnoreList([])
    
    # Test default patterns
    assert ignore_list.should_ignore("some_tarkov_item")
    assert ignore_list.should_ignore("diw_armor_plates_main_plate")
    
    # Test case insensitivity
    assert ignore_list.should_ignore("MMG")
    assert ignore_list.should_ignore("TARKOV_UPPERCASE")
    
    # Test non-matching items
    assert not ignore_list.should_ignore("ace_medical_bandage")
    assert not ignore_list.should_ignore("rhs_weapon")


def test_custom_ignore_patterns():
    """Test that custom ignore patterns work alongside defaults."""
    custom_patterns = [
        "ace_*",
        "*_backpack",
        "specific_item"
    ]
    
    ignore_list = EquipmentIgnoreList(custom_patterns)
    
    # Test custom patterns
    assert ignore_list.should_ignore("ace_medical_bandage")
    assert ignore_list.should_ignore("any_kind_of_backpack")
    assert ignore_list.should_ignore("specific_item")
    
    # Test that defaults still work
    assert ignore_list.should_ignore("rm")
    assert ignore_list.should_ignore("tarkov_item")
    
    # Test non-matching items
    assert not ignore_list.should_ignore("rhs_weapon")
    assert not ignore_list.should_ignore("tfar_radio")


def test_validator_integration():
    """Test that ignore patterns work in the validator."""
    validator = DependencyValidator(ignore_patterns=["test_*"])
    
    # Create test data
    scan_result = ScanResult()
    scan_result.equipment = {
        "test_ignore_this",
        "mmg",
        "keep_this_one",
        "tarkov_ignore_too"
    } # type: ignore
    
    classes = {
        "keep_this_one": {},  # Only this one should be checked
    }
    
    # Run validation
    result = validator._validate_single_mission(scan_result, classes, {})
    
    # Verify results
    assert "keep_this_one" in result.valid_classes
    assert len(result.missing_classes) == 0  # All others were ignored


def test_pattern_edge_cases():
    """Test edge cases and special patterns."""
    ignore_list = EquipmentIgnoreList([
        "*",            # Match everything
        "?test",       # Single character wildcard
        "[abc]_item",  # Character class
        ""            # Empty pattern
    ])
    
    assert ignore_list.should_ignore("anything")  # Matched by *
    assert ignore_list.should_ignore("atest")     # Matched by ?test
    assert ignore_list.should_ignore("b_item")    # Matched by [abc]_item
    assert not ignore_list.should_ignore("")      # Empty string


def test_ignore_pattern_inheritance():
    """Test that patterns are properly inherited from config."""
    global_patterns = ["global_*"]
    task_patterns = ["task_*"]
    
    validator = DependencyValidator(ignore_patterns=global_patterns + task_patterns)
    
    # Create test data
    scan_result = ScanResult()
    scan_result.equipment = {
        "global_ignore",
        "task_ignore",
        "mmg",        # From DEFAULT_IGNORED_EQUIPMENT
        "keep_this"
    }
    
    classes = {
        "keep_this": {},  # Only this should be checked
    }
    
    # Run validation
    result = validator._validate_single_mission(scan_result, classes, {})
    
    # Verify results
    assert "keep_this" in result.valid_classes
    assert len(result.missing_classes) == 0  # All others were ignored
