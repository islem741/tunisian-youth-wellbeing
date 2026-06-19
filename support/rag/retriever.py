"""RAG retrieval pipeline over WHO/UNICEF psychosocial guidelines.

Design principles:
- No external dependencies — pure Python string matching.
- Chunks are loaded from guidelines.txt, split by ## section headings.
- Each chunk carries its heading as a citation label.
- Confidence is normalised overlap: matched_words / total_query_words.
- Below the confidence threshold the pipeline abstains rather than
  hallucinating — an explicit "I don't know" is returned.
- The caller (view) must display citations; no answer is shown without them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_GUIDELINES_PATH = Path(__file__).parent / "guidelines.txt"
CONFIDENCE_THRESHOLD = 0.2   # abstain below this value


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    heading: str
    body: str

    @property
    def full_text(self) -> str:
        return f"{self.heading}\n{self.body}"


@dataclass
class RetrievalResult:
    answer: str
    citations: list[str] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def abstained(self) -> bool:
        return not self.citations


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_chunks(path: Path | None = None) -> list[Chunk]:
    """Parse guidelines.txt into Chunk objects.

    Each chunk begins with a line starting with ``##``.  Lines that do not
    start with ``##`` and appear before the first heading are ignored.
    """
    source = path or _GUIDELINES_PATH
    text = source.read_text(encoding="utf-8")

    chunks: list[Chunk] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            # Save the previous chunk before starting a new one
            if current_heading is not None:
                body = "\n".join(current_lines).strip()
                if body:
                    chunks.append(Chunk(heading=current_heading, body=body))
            current_heading = line[3:].strip()   # strip the "## " prefix
            current_lines = []
        else:
            if current_heading is not None:
                current_lines.append(line)

    # Flush the final chunk
    if current_heading is not None:
        body = "\n".join(current_lines).strip()
        if body:
            chunks.append(Chunk(heading=current_heading, body=body))

    return chunks


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _tokenise(text: str) -> set[str]:
    """Lowercase alphabetic tokens, ignoring stop-words."""
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "being", "to", "of", "and", "or", "in", "on", "at", "for",
        "with", "by", "as", "it", "its", "this", "that", "i", "you",
        "we", "they", "how", "what", "when", "where", "do", "does",
        "can", "will", "should", "would", "could", "not", "no",
    }
    words = {w.lower() for w in re.findall(r"[a-zA-Z]+", text)}
    return words - stop_words


def _score(query_words: set[str], chunk: Chunk) -> float:
    """Normalised keyword overlap: |query ∩ chunk| / |query|."""
    if not query_words:
        return 0.0
    chunk_words = _tokenise(chunk.full_text)
    matched = query_words & chunk_words
    return len(matched) / len(query_words)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def retrieve(query: str, top_k: int = 2) -> RetrievalResult:
    """Return the top-``top_k`` chunks most relevant to *query*.

    Returns a :class:`RetrievalResult`:
    - ``answer``     — concatenated chunk bodies, or abstention message.
    - ``citations``  — list of heading strings for the returned chunks.
    - ``confidence`` — normalised overlap score of the best-matching chunk.

    Abstention rule: if the best chunk scores below
    ``CONFIDENCE_THRESHOLD``, the pipeline abstains and returns no
    citations.  The caller must display citations alongside the answer.
    """
    if not query or not query.strip():
        return RetrievalResult(
            answer="Please enter a question.",
            citations=[],
            confidence=0.0,
        )

    chunks = load_chunks()
    query_words = _tokenise(query)

    if not query_words:
        return RetrievalResult(
            answer="Please enter a more specific question.",
            citations=[],
            confidence=0.0,
        )

    # Score every chunk
    scored: list[tuple[float, Chunk]] = [
        (_score(query_words, chunk), chunk)
        for chunk in chunks
    ]
    scored.sort(key=lambda t: t[0], reverse=True)

    best_score = scored[0][0] if scored else 0.0

    # Abstain if confidence is too low
    if best_score < CONFIDENCE_THRESHOLD:
        return RetrievalResult(
            answer=(
                "I don't have enough information to answer this reliably. "
                "Please consult your supervising counselor."
            ),
            citations=[],
            confidence=best_score,
        )

    # Take top-k chunks with non-zero score
    top = [(score, chunk) for score, chunk in scored[:top_k] if score > 0]

    answer_parts = [chunk.body for _, chunk in top]
    citations    = [chunk.heading for _, chunk in top]

    return RetrievalResult(
        answer="\n\n".join(answer_parts),
        citations=citations,
        confidence=round(best_score, 3),
    )
