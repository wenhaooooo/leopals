"""Shared test fixtures for LeoPals test suite."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_llm():
    """Mock LLM that returns predictable responses."""
    llm = AsyncMock()
    response = MagicMock()
    response.content = '{"intent": "qa"}'
    llm.ainvoke.return_value = response
    return llm


@pytest.fixture
def sample_dense_results():
    """Sample vector search results."""
    return [
        (1, 0.95, {"content": "奖学金申请条件", "doc_metadata": {"category": "教务"}}),
        (2, 0.88, {"content": "奖学金评定流程", "doc_metadata": {"category": "教务"}}),
        (3, 0.75, {"content": "校历安排", "doc_metadata": {"category": "校务"}}),
    ]


@pytest.fixture
def sample_sparse_results():
    """Sample BM25 search results."""
    return [
        (2, 3.5, {"content": "奖学金评定流程", "doc_metadata": {"category": "教务"}}),
        (4, 2.1, {"content": "奖学金发放时间", "doc_metadata": {"category": "财务"}}),
        (1, 1.8, {"content": "奖学金申请条件", "doc_metadata": {"category": "教务"}}),
    ]


@pytest.fixture
def mock_embedding_client():
    """Mock embedding client that returns fixed vectors."""
    client = AsyncMock()
    client.embed_documents.return_value = [[0.1] * 768, [0.2] * 768]
    client.embed_query.return_value = [0.15] * 768
    return client
