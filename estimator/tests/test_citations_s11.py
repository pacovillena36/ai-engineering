"""Tests for Session 11 per-line citation verification.

Covers verify_citations: dangling detection, integrity violations, grounding
status classification, and optional chunk-level validation (evidence matching,
document_id verification).
"""

from __future__ import annotations

import pytest

from app.generation.rag.schemas import (
    Assumption,
    Estimate,
    SourceCitation,
    SourceReference,
    TaskItem,
    WorkModule,
)
from app.generation.rag.validation import verify_citations


def test_all_lines_grounded_correctly():
    """All lines cite chunks that are in the retrieved set → all grounded."""
    estimate = Estimate(
        total_engineer_days=50,
        confidence="high",
        reasoning="Grounded in historical budgets.",
        modules=[
            WorkModule(
                name="Auth",
                tasks=[
                    TaskItem(
                        name="OAuth 2.0 backend",
                        engineer_days=20,
                        grounded=True,
                        sources=[
                            SourceReference(
                                chunk_id="101",
                                document_id="BUD-001",
                                evidence="OAuth 2.0 authentication, 160h",
                            )
                        ],
                    ),
                    TaskItem(
                        name="SCA",
                        engineer_days=30,
                        grounded=True,
                        sources=[
                            SourceReference(
                                chunk_id="102",
                                document_id="BUD-001",
                                evidence="Strong customer authentication, 240h",
                            )
                        ],
                    ),
                ],
            )
        ],
    )
    retrieved_ids = {"101", "102"}
    report = verify_citations(estimate, retrieved_ids)

    assert report.total_lines == 2
    assert report.grounded_lines == 2
    assert report.dangling_lines == 0
    assert report.insufficient_lines == 0
    assert report.verified_citations == 2
    assert report.dangling_citations == []
    assert not report.has_dangling


def test_dangling_citation_detected():
    """Line cites a chunk_id never retrieved → dangling status."""
    estimate = Estimate(
        total_engineer_days=20,
        confidence="high",
        reasoning="Mostly grounded.",
        modules=[
            WorkModule(
                name="Auth",
                tasks=[
                    TaskItem(
                        name="OAuth",
                        engineer_days=20,
                        grounded=True,
                        sources=[
                            SourceReference(
                                chunk_id="999",  # Never retrieved
                                document_id="BUD-999",
                                evidence="Invented source",
                            )
                        ],
                    ),
                ],
            )
        ],
    )
    retrieved_ids = {"101", "102"}
    report = verify_citations(estimate, retrieved_ids)

    assert report.total_lines == 1
    assert report.grounded_lines == 0
    assert report.dangling_lines == 1
    assert report.insufficient_lines == 0
    assert report.verified_citations == 0
    assert report.dangling_citations == ["999"]
    assert report.has_dangling


def test_ungrounded_line_marked_correctly():
    """Line grounded=False with empty sources → insufficient status."""
    estimate = Estimate(
        total_engineer_days=20,
        confidence="high",
        reasoning="Partial coverage.",
        modules=[
            WorkModule(
                name="Compliance",
                tasks=[
                    TaskItem(
                        name="Regulatory reporting",
                        engineer_days=None,
                        grounded=False,
                        sources=[],
                    ),
                ],
            )
        ],
        assumptions=[
            Assumption(
                description="Regulatory reporting framework TBD",
                impact="high",
                rationale="No historical analog in corpus",
            )
        ],
    )
    retrieved_ids = {"101"}
    report = verify_citations(estimate, retrieved_ids)

    assert report.total_lines == 1
    assert report.grounded_lines == 0
    assert report.dangling_lines == 0
    assert report.insufficient_lines == 1
    assert report.verified_citations == 0
    assert report.dangling_citations == []
    assert not report.has_dangling


def test_mixed_line_statuses():
    """Estimate with grounded, dangling, and insufficient lines."""
    estimate = Estimate(
        total_engineer_days=50,
        confidence="medium",
        reasoning="Mixed grounding.",
        modules=[
            WorkModule(
                name="Module1",
                tasks=[
                    TaskItem(
                        name="Task1",
                        engineer_days=20,
                        grounded=True,
                        sources=[
                            SourceReference(
                                chunk_id="101",
                                document_id="BUD-001",
                                evidence="Component A, 160h",
                            )
                        ],
                    ),
                    TaskItem(
                        name="Task2",
                        engineer_days=15,
                        grounded=True,
                        sources=[
                            SourceReference(
                                chunk_id="999",  # Dangling
                                document_id="BUD-999",
                                evidence="Made up",
                            )
                        ],
                    ),
                    TaskItem(
                        name="Task3",
                        engineer_days=None,
                        grounded=False,
                        sources=[],
                    ),
                ],
            )
        ],
    )
    retrieved_ids = {"101", "102"}
    report = verify_citations(estimate, retrieved_ids)

    assert report.total_lines == 3
    assert report.grounded_lines == 1
    assert report.dangling_lines == 1
    assert report.insufficient_lines == 1
    assert report.verified_citations == 1
    assert report.dangling_citations == ["999"]
    assert report.has_dangling


def test_multiple_sources_per_line():
    """Line cites multiple chunks, one valid and one dangling."""
    estimate = Estimate(
        total_engineer_days=30,
        confidence="high",
        reasoning="Multi-source",
        modules=[
            WorkModule(
                name="Module",
                tasks=[
                    TaskItem(
                        name="Task",
                        engineer_days=30,
                        grounded=True,
                        sources=[
                            SourceReference(
                                chunk_id="101",
                                document_id="BUD-001",
                                evidence="Component A",
                            ),
                            SourceReference(
                                chunk_id="999",
                                document_id="BUD-999",
                                evidence="Component B",
                            ),
                        ],
                    ),
                ],
            )
        ],
    )
    retrieved_ids = {"101", "102"}
    report = verify_citations(estimate, retrieved_ids)

    assert report.total_lines == 1
    assert report.grounded_lines == 0  # Has dangling, so not fully grounded
    assert report.dangling_lines == 1
    assert report.verified_citations == 1  # One valid citation
    assert report.dangling_citations == ["999"]


def test_estimate_global_sources_verified():
    """Estimate-level SourceCitation ids are also verified."""
    estimate = Estimate(
        total_engineer_days=20,
        confidence="high",
        reasoning="Grounded.",
        modules=[
            WorkModule(
                name="Module",
                tasks=[
                    TaskItem(
                        name="Task",
                        engineer_days=20,
                        grounded=True,
                        sources=[
                            SourceReference(
                                chunk_id="101",
                                document_id="BUD-001",
                                evidence="Component A",
                            )
                        ],
                    ),
                ],
            )
        ],
        sources=[
            SourceCitation(source_id=101, relevance="primary", used_for="architecture"),
            SourceCitation(source_id=999, relevance="supporting", used_for="fallback"),
        ],
    )
    retrieved_ids = {"101", "102"}
    report = verify_citations(estimate, retrieved_ids)

    # The dangling estimate-level citation should be detected
    assert report.has_dangling
    assert "999" in report.dangling_citations


def test_empty_estimate_is_valid():
    """Estimate with no modules or sources → clean."""
    estimate = Estimate(
        total_engineer_days=None,
        confidence="insufficient",
        reasoning="No context.",
        insufficient_context_explanation="Retrieval failed.",
    )
    retrieved_ids = set()
    report = verify_citations(estimate, retrieved_ids)

    assert report.total_lines == 0
    assert report.grounded_lines == 0
    assert report.dangling_lines == 0
    assert report.insufficient_lines == 0
    assert report.verified_citations == 0
    assert report.dangling_citations == []
    assert not report.has_dangling


def test_line_citation_report_detail():
    """CitationReport per-line details are populated correctly."""
    estimate = Estimate(
        total_engineer_days=20,
        confidence="high",
        reasoning="Test",
        modules=[
            WorkModule(
                name="Auth",
                tasks=[
                    TaskItem(
                        name="OAuth",
                        engineer_days=20,
                        grounded=True,
                        sources=[
                            SourceReference(
                                chunk_id="101",
                                document_id="BUD-001",
                                evidence="OAuth",
                            )
                        ],
                    ),
                ],
            )
        ],
    )
    retrieved_ids = {"101"}
    report = verify_citations(estimate, retrieved_ids)

    assert len(report.lines) == 1
    line = report.lines[0]
    assert line.module == "Auth"
    assert line.component == "OAuth"
    assert line.status == "grounded"
    assert line.cited_chunk_ids == ["101"]
    assert line.dangling_chunk_ids == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
