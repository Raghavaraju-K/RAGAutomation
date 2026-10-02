Feature: RAG evaluation gates for release
  As a release manager
  I want the 100-question framework to gate releases
  So that Recall, Faithfulness, Relevance, Hallucination and Latency are enforced

  Scenario: Gate - Recall@5 at least 90 percent
    Given a completed 100-question evaluation report
    Then Recall@5 is at least 0.90

  Scenario: Gate - Faithfulness at least 90 percent
    Given a completed 100-question evaluation report
    Then Faithfulness is at least 0.90

  Scenario: Gate - Answer relevance at least 90 percent
    Given a completed 100-question evaluation report
    Then Answer relevance is at least 0.90

  Scenario: Gate - Hallucination at most 5 percent
    Given a completed 100-question evaluation report
    Then Hallucination is at most 0.05

  Scenario: Gate - P95 latency at most 3 seconds
    Given a completed 100-question evaluation report
    Then P95 latency is at most 3.0 seconds

  Scenario: Gate - overall verdict is PASS and dataset has 100 UK questions
    Given a completed 100-question evaluation report
    Then the verdict is "PASS" with 100 per-question rows
