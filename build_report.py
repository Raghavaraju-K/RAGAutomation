"""Build the visual automation dashboard from a JUnit XML + the RAG eval report.

Automation tests only: developer-owned unit tests (tests/test_units.py) are excluded
by default; pass --include-unit if you explicitly want them in the report.
"""
from src.reporting.report_builder import build

if __name__ == "__main__":
    from src.reporting import report_builder as _rb
    _rb.main()