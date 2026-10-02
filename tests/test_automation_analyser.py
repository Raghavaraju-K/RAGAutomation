"""Imperative automation: memo analyser — strong/weak memos, pdf path, checklist shape.

Best practice: decision-table testing of the 8 UK checks; strong vs weak
equivalence classes; contract test on checklist/evidence schema.
BDD mirror: tests/bdd/features/memo_analysis.feature
"""
import pytest

from tests.helpers.checks import (
    analyse_text, analyse_file, assert_checklist_shape, assert_evidence_cites_uk,
)

pytestmark = [pytest.mark.analyser, pytest.mark.integration]


def test_strong_memo_ready_for_review(sample_text):
    res = analyse_text(sample_text)
    assert res["overall_score"] >= 0.6, res
    assert res["verdict"] == "READY FOR REVIEW", res
    assert_checklist_shape(res)
    assert len(res["standards_evidence"]) == 4
    assert_evidence_cites_uk(res)


@pytest.mark.negative
def test_weak_memo_needs_work(weak_text):
    res = analyse_text(weak_text)
    assert res["verdict"] == "NEEDS WORK BEFORE COMMITTEE", res
    assert len(res["gaps"]) >= 3, res


@pytest.mark.negative
def test_empty_memo_error():
    from src.memo_analyser import analyse_memo
    assert "error" in analyse_memo("   ", is_text=True)


def test_pdf_memo_end_to_end(sample_pdf):
    res = analyse_file(sample_pdf)
    assert "verdict" in res, res
    assert res["overall_score"] >= 0.5, res
    assert res["memo_chars"] > 200


@pytest.mark.edge
def test_missing_file_error(tmp_path):
    res = analyse_file(str(tmp_path / "nope.pdf"))
    assert "error" in res


@pytest.mark.parametrize("probe,expected", [
    ("consumer duty fair value", True),
    ("ifrs 9", True),
    ("stage 1", True),
    ("companies house", True),
    ("21 days", True),
    ("debenture", True),
    ("basel xyz nonsense", False),
])
def test_checklist_hits_key_phrases(sample_text, probe, expected):
    from src.memo_analyser import _score
    hits, sc = _score(sample_text, [probe])
    assert (sc == 1.0) is expected, (probe, hits)
