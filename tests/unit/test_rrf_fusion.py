"""Unit tests for RRF (Reciprocal Rank Fusion) algorithm."""

import pytest
from collections import defaultdict


class TestRRFFusion:
    """Test the _rrf_fusion algorithm from PgVectorHybridRetriever."""

    def _rrf_fusion(self, dense_results, sparse_results, k=60):
        """Standalone copy of the RRF algorithm for testing."""
        scores = defaultdict(float)
        doc_map = {}

        for rank, (doc_id, score, payload) in enumerate(dense_results):
            scores[doc_id] += 1.0 / (k + rank + 1)
            doc_map[doc_id] = payload

        for rank, (doc_id, score, payload) in enumerate(sparse_results):
            scores[doc_id] += 1.0 / (k + rank + 1)
            if doc_id not in doc_map:
                doc_map[doc_id] = payload

        combined = [(doc_id, score, doc_map[doc_id]) for doc_id, score in scores.items()]
        combined.sort(key=lambda x: x[1], reverse=True)
        return combined

    def test_doc_in_both_ranks_highest(self, sample_dense_results, sample_sparse_results):
        """Doc appearing in both result sets should rank highest."""
        fused = self._rrf_fusion(sample_dense_results, sample_sparse_results, k=60)
        assert fused[0][0] == 2

    def test_all_docs_preserved(self, sample_dense_results, sample_sparse_results):
        """All unique documents from both sets should appear in output."""
        fused = self._rrf_fusion(sample_dense_results, sample_sparse_results, k=60)
        fused_ids = {doc_id for doc_id, _, _ in fused}
        dense_ids = {doc_id for doc_id, _, _ in sample_dense_results}
        sparse_ids = {doc_id for doc_id, _, _ in sample_sparse_results}
        assert fused_ids == dense_ids | sparse_ids

    def test_empty_dense(self, sample_sparse_results):
        """Empty dense results should return sparse results only."""
        fused = self._rrf_fusion([], sample_sparse_results, k=60)
        assert len(fused) == len(sample_sparse_results)
        assert fused[0][0] == sample_sparse_results[0][0]

    def test_empty_sparse(self, sample_dense_results):
        """Empty sparse results should return dense results only."""
        fused = self._rrf_fusion(sample_dense_results, [], k=60)
        assert len(fused) == len(sample_dense_results)
        assert fused[0][0] == sample_dense_results[0][0]

    def test_both_empty(self):
        """Both empty should return empty list."""
        fused = self._rrf_fusion([], [], k=60)
        assert fused == []

    def test_no_overlap(self):
        """No overlapping docs should produce simple rank merge."""
        dense = [(10, 0.9, {"content": "A"}), (20, 0.8, {"content": "B"})]
        sparse = [(30, 3.0, {"content": "C"}), (40, 2.0, {"content": "D"})]
        fused = self._rrf_fusion(dense, sparse, k=60)
        assert len(fused) == 4
        top_ids = {fused[0][0], fused[1][0]}
        assert top_ids == {10, 30}

    def test_score_values_ignored(self):
        """RRF should ignore actual score values, only use rank positions."""
        dense = [(1, 0.1, {"content": "low score, rank 0"}), (2, 0.99, {"content": "high score, rank 1"})]
        sparse = [(2, 0.1, {"content": "low score, rank 0"}), (1, 0.99, {"content": "high score, rank 1"})]
        fused = self._rrf_fusion(dense, sparse, k=60)
        scores = {doc_id: score for doc_id, score, _ in fused}
        assert abs(scores[1] - scores[2]) < 1e-10

    def test_k_parameter_affects_scores(self):
        """Different k values should produce different score distributions."""
        dense = [(1, 0.9, {"content": "A"}), (2, 0.8, {"content": "B"})]
        sparse = [(1, 3.0, {"content": "A"}), (2, 2.0, {"content": "B"})]
        fused_k10 = self._rrf_fusion(dense, sparse, k=10)
        fused_k100 = self._rrf_fusion(dense, sparse, k=100)
        score_diff_k10 = fused_k10[0][1] - fused_k10[1][1]
        score_diff_k100 = fused_k100[0][1] - fused_k100[1][1]
        assert score_diff_k10 > score_diff_k100
