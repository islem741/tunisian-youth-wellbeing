"""Tests for the upgraded RAG retrieval pipeline.

Covers:
1. Known-topic query returns at least one citation.
2. Out-of-domain query abstains (low confidence, empty citations).
3. Non-abstaining results always carry at least one citation.
4. load_chunks() returns the expected number of sections with headings.
5. RetrievalResult.abstained property works correctly.
6. Confidence is bounded to [0, 1].
7. retrieve() with an empty string does not crash and returns empty citations.
"""

from __future__ import annotations

import pytest

from support.rag.retriever import (
    CONFIDENCE_THRESHOLD,
    RetrievalResult,
    load_chunks,
    retrieve,
)


# ---------------------------------------------------------------------------
# 1. Known topic — at least one citation returned
# ---------------------------------------------------------------------------

def test_retriever_returns_citation_for_known_topic():
    """'how to handle crisis' should match the Crisis De-Escalation chunk."""
    result = retrieve("how to handle crisis")
    assert len(result.citations) >= 1, (
        f"Expected ≥1 citation, got {result.citations!r} "
        f"(confidence={result.confidence})"
    )
    # The answer text must be non-empty when citations exist
    assert result.answer.strip()


# ---------------------------------------------------------------------------
# 2. Out-of-domain query — abstention
# ---------------------------------------------------------------------------

def test_retriever_abstains_on_unknown_topic():
    """'stock market prices' is unrelated to psychosocial guidelines."""
    result = retrieve("stock market prices")
    assert result.citations == [], (
        f"Expected empty citations for off-topic query, got {result.citations!r}"
    )
    assert result.confidence < CONFIDENCE_THRESHOLD
    assert result.abstained is True
    # Abstention message must be present
    assert len(result.answer) > 0


# ---------------------------------------------------------------------------
# 3. Non-abstaining results always have citations
# ---------------------------------------------------------------------------

KNOWN_QUERIES = [
    "active listening techniques",
    "escalate crisis immediate risk",
    "confidentiality boundaries peer supporter",
    "safe messaging mental health",
    "trauma informed care response",
]


@pytest.mark.parametrize("query", KNOWN_QUERIES)
def test_retriever_never_returns_answer_without_citation(query):
    """For any confident result, citations list must be non-empty."""
    result = retrieve(query)
    if not result.abstained:
        assert result.citations, (
            f"Non-abstaining result for '{query}' has empty citations"
        )
        assert result.answer.strip(), (
            f"Non-abstaining result for '{query}' has empty answer"
        )


# ---------------------------------------------------------------------------
# 4. load_chunks parses ## headings correctly
# ---------------------------------------------------------------------------

def test_load_chunks_returns_expected_count():
    """guidelines.txt has 12 ## sections."""
    chunks = load_chunks()
    assert len(chunks) >= 10, f"Expected ≥10 chunks, got {len(chunks)}"


def test_load_chunks_headings_are_non_empty():
    """Every chunk must have a non-empty heading and body."""
    for chunk in load_chunks():
        assert chunk.heading.strip(), "Empty heading found"
        assert chunk.body.strip(),    "Empty body found"


def test_load_chunks_headings_do_not_start_with_hash():
    """The ## prefix must be stripped from the heading."""
    for chunk in load_chunks():
        assert not chunk.heading.startswith("#"), (
            f"Heading still contains '#': {chunk.heading!r}"
        )


# ---------------------------------------------------------------------------
# 5. RetrievalResult.abstained property
# ---------------------------------------------------------------------------

def test_abstained_property_true_when_no_citations():
    r = RetrievalResult(answer="Sorry.", citations=[], confidence=0.05)
    assert r.abstained is True


def test_abstained_property_false_when_citations_present():
    r = RetrievalResult(answer="See below.", citations=["Active Listening"],
                        confidence=0.6)
    assert r.abstained is False


# ---------------------------------------------------------------------------
# 6. Confidence is bounded
# ---------------------------------------------------------------------------

def test_confidence_bounded_between_0_and_1():
    for query in KNOWN_QUERIES + ["xyznotaword qrstuv"]:
        result = retrieve(query)
        assert 0.0 <= result.confidence <= 1.0, (
            f"Confidence out of range for '{query}': {result.confidence}"
        )


# ---------------------------------------------------------------------------
# 7. Edge cases — empty / whitespace query
# ---------------------------------------------------------------------------

def test_empty_query_returns_empty_citations():
    result = retrieve("")
    assert result.citations == []


def test_whitespace_query_returns_empty_citations():
    result = retrieve("   ")
    assert result.citations == []
