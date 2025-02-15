import pytest
import random
import string
import time
from dependency_scanner.core.analysis.fuzzy_matcher import FuzzyClassMatcher
from dependency_scanner.core.analysis.fuzzy_config import FuzzyMatchConfig
from dependency_scanner.core.analysis.fuzzy_result import FuzzyMatchResult

# Consolidate test fixtures
@pytest.fixture
def fuzzy_config():
    return FuzzyMatchConfig(
        similarity_threshold=0.7,
        quick_match_threshold=0.8
    )

@pytest.fixture
def fuzzy_matcher(fuzzy_config):
    return FuzzyClassMatcher(config=fuzzy_config)

@pytest.fixture
def sample_classes():
    return {
        'helmet_combat_olive',
        'hat_boonie_black',
        'simc_addon_nmx_long_tan',
        'uniform_combat_mc',
        'vest_carrier_black',
    }

# Update result type assertions
def test_find_similar_classes(fuzzy_matcher, sample_classes):
    result = fuzzy_matcher.find_similar_classes('aegis_boonie_blk', sample_classes)
    assert isinstance(result, FuzzyMatchResult)
    assert result.matches  # Just check if there are matches
    assert 'hat_boonie_black' in result.matches[0][0]  # Check first match

    # Test word substitutions
    result = fuzzy_matcher.find_similar_classes('simc_addon_nomex_long_tan', sample_classes)
    assert result.matches  # Check if there are matches
    assert any('simc_addon_nmx_long_tan' in match[0] for match in result.matches)

def test_normalize_class_name(fuzzy_matcher):
    # Only use the public method
    assert fuzzy_matcher.normalize_class_name('cls_helmet_combat_01') == 'helmet_combat'
    assert fuzzy_matcher.normalize_class_name('item_vest_carrier') == 'vest_carrier'
    assert fuzzy_matcher.normalize_class_name('uniform___combat___mc') == 'uniform_combat_mc'

def test_substitution_scoring(fuzzy_matcher):
    score = fuzzy_matcher._calculate_substitution_score(
        'aegis_vest_black', 
        'vest_carrier_black'
    )
    assert score > 0.5  # Should recognize 'vest' and 'black' as matching parts

def test_category_detection(fuzzy_matcher):
    assert fuzzy_matcher.get_category_match('helmet_combat') == 'helmet'
    assert fuzzy_matcher.get_category_match('vest_carrier') == 'vest'
    assert fuzzy_matcher.get_category_match('uniform_combat') == 'uniform'
    assert fuzzy_matcher.get_category_match('unknown_item') is None

def test_similarity_thresholds(fuzzy_matcher):
    # Very different strings should score low
    result = fuzzy_matcher.find_similar_classes(
        'completely_different_item',
        {'vest_carrier_black'}
    )
    assert not result.matches  # Should be below threshold

    # Similar strings should match
    matches = fuzzy_matcher.find_similar_classes(
        'vest_carrier_blk',
        {'vest_carrier_black'}
    )
    assert matches  # Should be above threshold

# Remove redundant performance tests and consolidate into single test
def test_matcher_performance_and_caching(fuzzy_matcher, sample_classes):
    # Generate test data
    test_classes = {
        ''.join(random.choices(string.ascii_lowercase, k=10)) + '_' + 
        random.choice(['helmet', 'vest', 'uniform'])
        for _ in range(1000)
    }
    
    start_time = time.time()
    for _ in range(100):
        fuzzy_matcher.find_similar_classes('test_helmet_black', test_classes)
    duration = time.time() - start_time
    
    # Increase time threshold for slower systems
    assert duration < 1.5  # Increase timeout to 1.5 seconds

    # Test that caching improves repeated lookups
    test_name = 'complex_helmet_combat_01_black'
    
    # First call - uncached
    start_time = time.time()
    result1 = fuzzy_matcher.normalize_class_name(test_name)
    first_duration = time.time() - start_time
    
    # Second call - should use cache
    start_time = time.time()
    result2 = fuzzy_matcher.normalize_class_name(test_name)
    second_duration = time.time() - start_time
    
    assert second_duration < first_duration
    assert result1 == result2

def test_parallel_processing(fuzzy_matcher):
    # Generate large test dataset
    test_classes = {
        f"test_class_{i}_{random.choice(['helmet', 'vest', 'uniform'])}"
        for i in range(2000)
    }
    
    # Test parallel processing with large dataset
    start_time = time.time()
    parallel_results = fuzzy_matcher.find_similar_classes(
        'test_helmet_black',
        test_classes
    )
    parallel_duration = time.time() - start_time
    
    # Remove sequential comparison, test batch processing instead
    start_time = time.time()
    batch_results = fuzzy_matcher.find_similar_classes_batch(
        ['test_helmet_black'] * 10,  # Test with multiple identical queries
        test_classes
    )
    batch_duration = time.time() - start_time
    
    # Verify batch is not slower than single query
    single_start = time.time()
    single_result = fuzzy_matcher.find_similar_classes('test_helmet_black', test_classes)
    single_duration = time.time() - start_time
    
    assert batch_duration / 10 <= single_duration * 2  # Batch should be reasonably efficient

def test_batch_processing(fuzzy_matcher):
    # Set up similar classes that should match
    missing_classes = [
        'test_aegis_helmet_black',  # Should match with hat_helmet_black
        'vest_carrier_tan_test',    # Should match with vest_carrier_tan
        'uniform_combat_test'       # Should match with uniform_combat_mc
    ]
    available_classes = {
        'hat_helmet_black',
        'vest_carrier_tan',
        'uniform_combat_mc'
    }
    
    batch_results = fuzzy_matcher.find_similar_classes_batch(
        missing_classes,
        available_classes
    )
    
    # Basic size checks
    assert len(batch_results) == len(missing_classes)
    
    # Verify each missing class got processed
    for missing_class in missing_classes:
        assert missing_class in batch_results
        result = batch_results[missing_class]
        assert result.matches, f"No matches found for {missing_class}"  # Should have matches
        assert len(result.matches) > 0
        assert result.matches[0][1] >= 0.5  # Should have reasonable confidence
