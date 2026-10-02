"""Build the presentation-grade Automation Strategy document (self-contained HTML).

Output: docs/automation_strategy.html - open it, present it, or Ctrl+P to save as PDF.
"""
from src.reporting.strategy_doc import build

if __name__ == "__main__":
    from src.reporting import strategy_doc as _sd
    _sd.main()