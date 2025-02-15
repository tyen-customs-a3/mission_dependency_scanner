from typing import Set, List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re
from difflib import SequenceMatcher
from functools import lru_cache
import logging

from .fuzzy_config import FuzzyMatchConfig
from .fuzzy_result import FuzzyMatchResult

logger = logging.getLogger(__name__)

class FuzzyClassMatcher:
    """Enhanced fuzzy matching for class names."""
    
    def __init__(self, config: Optional[FuzzyMatchConfig] = None):
        self.config = config or FuzzyMatchConfig()
        self._reverse_substitutions = self._build_reverse_substitutions()
        self._compile_patterns()
        self.max_workers = min(32, (os.cpu_count() or 1) + 4)
        
    def _compile_patterns(self) -> None:
        """Compile regex patterns once at initialization."""
        self._patterns = {
            'prefix': re.compile(r'^(cls_|class_|item_)'),
            'number': re.compile(r'_\d+$'),
            'underscore': re.compile(r'_+'),
            'splitter': re.compile(r'[_\s]+')
        }

    def _build_reverse_substitutions(self) -> Dict[str, str]:
        """Build reverse lookup for word substitutions."""
        reverse = {}
        for base_word, substitutes in self.config.word_substitutions.items():
            for sub in substitutes:
                reverse[sub] = base_word
        return reverse

    @lru_cache(maxsize=1024)
    def normalize_class_name(self, class_name: str) -> str:
        """Normalize class name for comparison with caching."""
        normalized = class_name.lower()
        normalized = self._patterns['prefix'].sub('', normalized)
        normalized = self._patterns['number'].sub('', normalized)
        normalized = self._patterns['underscore'].sub('_', normalized)
        return normalized.strip('_')

    def find_similar_classes(self, query: str, candidates: Set[str], 
                           max_suggestions: int = 3) -> FuzzyMatchResult:
        """Find similar class names with detailed matching information."""
        normalized_query = self.normalize_class_name(query)
        query_parts = set(self._patterns['splitter'].split(query.lower()))
        category = self._detect_category(query)
        
        # Quick exact/substitution matches
        direct_matches = self._find_direct_matches(normalized_query, candidates)
        if direct_matches:
            return FuzzyMatchResult(
                original=query,
                matches=direct_matches[:max_suggestions],
                category=category,
                normalized_form=normalized_query,
                match_type='direct'
            )
            
        # Filtered candidate search
        filtered_candidates = self._filter_candidates(query, category, query_parts, candidates)
        
        # Detailed scoring
        scored_matches = self._score_candidates(
            normalized_query, query, filtered_candidates
        )
        
        return FuzzyMatchResult(
            original=query,
            matches=scored_matches[:max_suggestions],
            category=category,
            normalized_form=normalized_query,
            match_type='fuzzy'
        )

    def find_similar_classes_batch(self, queries: List[str], 
                                 candidates: Set[str],
                                 max_suggestions: int = 3) -> Dict[str, FuzzyMatchResult]:
        """Process multiple queries in parallel."""
        # Initialize results dict with empty results for all queries
        results = {
            query: FuzzyMatchResult(
                original=query,
                matches=[],
                normalized_form=self.normalize_class_name(query)
            ) for query in queries
        }
        
        candidates = set(candidates)  # Ensure we have a set
        
        # Process queries in batches
        if len(queries) > 100:
            chunk_size = max(100, len(queries) // self.max_workers)
            chunks = [queries[i:i + chunk_size] 
                     for i in range(0, len(queries), chunk_size)]
            
            # Process chunks in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_chunk = {
                    executor.submit(self._process_batch_chunk, chunk, candidates, max_suggestions): chunk
                    for chunk in chunks
                }
                
                for future in as_completed(future_to_chunk):
                    try:
                        chunk_results = future.result()
                        results.update(chunk_results)  # Update with any found matches
                    except Exception as e:
                        logger.error(f"Error processing chunk: {e}")
        else:
            # Process sequentially for small inputs
            for query in queries:
                # Update existing result entry
                results[query] = self.find_similar_classes(query, candidates, max_suggestions)
                    
        return results

    def _process_batch_chunk(self, chunk: List[str], candidates: Set[str],
                           max_suggestions: int) -> Dict[str, FuzzyMatchResult]:
        """Process a chunk of queries."""
        results = {}
        for query in chunk:
            try:
                # Always store result regardless of matches
                results[query] = self.find_similar_classes(query, candidates, max_suggestions)
            except Exception as e:
                logger.error(f"Error processing {query}: {e}")
                # Return empty result on error
                results[query] = FuzzyMatchResult(
                    original=query,
                    matches=[],
                    normalized_form=query
                )
        return results

    def _detect_category(self, class_name: str) -> Optional[str]:
        """Detect the category of a class name."""
        parts = set(self._patterns['splitter'].split(class_name.lower()))
        
        for category, keywords in self.config.categories.items():
            if keywords & parts:
                return category
        return None

    def _find_direct_matches(self, normalized_query: str, candidates: Set[str]) -> List[Tuple[str, float]]:
        """Find direct matches or substitution matches."""
        matches = []
        for candidate in candidates:
            normalized_candidate = self.normalize_class_name(candidate)
            if normalized_candidate == normalized_query:
                matches.append((candidate, 1.0))
            elif self._calculate_substitution_score(normalized_query, normalized_candidate) > 0.8:
                matches.append((candidate, 0.8))
        return matches

    def _filter_candidates(self, query: str, category: Optional[str],
                         query_parts: Set[str], candidates: Set[str]) -> Set[str]:
        """Filter candidates based on quick checks."""
        filtered = set()
        
        for candidate in candidates:
            # Skip exact matches and empty strings
            if not candidate or candidate == query:
                continue
                
            # Category check
            if category:
                candidate_category = self._detect_category(candidate)
                if candidate_category and candidate_category != category:
                    continue
            
            # Word overlap check
            candidate_parts = set(self._patterns['splitter'].split(candidate.lower()))
            if query_parts & candidate_parts:
                filtered.add(candidate)
                
        return filtered

    def _score_candidates(self, normalized_query: str, query: str,
                        candidates: Set[str]) -> List[Tuple[str, float]]:
        """Score candidates based on similarity."""
        matches = []
        for candidate in candidates:
            score = self._calculate_similarity_score(
                normalized_query,
                query,
                candidate
            )
            
            if score >= self.config.similarity_threshold:
                matches.append((candidate, score))
                
                # Early exit on high confidence
                if len(matches) >= self.config.max_suggestions and all(m[1] > 0.9 for m in matches):
                    break

        return sorted(matches, key=lambda x: x[1], reverse=True)[:self.config.max_suggestions]

    def _calculate_similarity_score(self, normalized_query: str, query: str,
                                 candidate: str) -> float:
        """Calculate final similarity score."""
        candidate_norm = self.normalize_class_name(candidate)
        
        # Base similarity using sequence matcher
        base_score = SequenceMatcher(None, normalized_query, candidate_norm).ratio()
        
        # Word substitution bonus
        sub_score = self._calculate_substitution_score(query, candidate)
        
        # Weighted combination
        return (base_score * 0.7) + (sub_score * 0.3)

    def _calculate_substitution_score(self, original: str, candidate: str) -> float:
        """Calculate word substitution similarity score."""
        original_parts = set(self._patterns['splitter'].split(original.lower()))
        candidate_parts = set(self._patterns['splitter'].split(candidate.lower()))
        
        score = sum(
            1.0 if part in candidate_parts else
            0.8 if any(sub in candidate_parts 
                      for sub in self.config.word_substitutions.get(part, set())) or
                 self._reverse_substitutions.get(part) in candidate_parts
            else 0.0
            for part in original_parts
        )
        
        return score / len(original_parts) if original_parts else 0.0

    def get_category_match(self, class_name: str) -> Optional[str]:
        """Public method to detect class category."""
        return self._detect_category(class_name)

    def _find_similar_classes_sequential(self, query: str, 
                                      candidates: Set[str],
                                      max_suggestions: int) -> List[Tuple[str, float]]:
        """Sequential processing for testing comparison."""
        result = self.find_similar_classes(query, candidates, max_suggestions)
        return result.matches if result else []
