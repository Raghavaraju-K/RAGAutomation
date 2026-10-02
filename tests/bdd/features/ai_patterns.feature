Feature: AI-specific testing patterns for the RAG app
  As a QA engineer for AI apps
  I want retrieval, grounding, bias, robustness and determinism checks
  So that quality gates mean something for a non-deterministic system

  Scenario: Retrieval - gold document is recalled in top-5
    Given the UK knowledge base is indexed
    When I search "PRA SS13/16 ICR 125 percent 5.5 percent"
    Then "uk_12_affordability_btl.txt" is in the top 5

  Scenario: Groundedness - answer sentences come from retrieved context
    Given the UK knowledge base is indexed
    When I ask "What is the PRA minimum ICR and stressed rate for buy-to-let?"
    Then faithfulness of the answer to its contexts is 1.0

  Scenario: No-leakage - user memos are never indexed
    Given the UK knowledge base is indexed
    Then the index contains only UK standards documents
    And "data/memos" files are absent from the index

  Scenario: Robustness - typo-tolerant question still answers
    Given the UK knowledge base is indexed
    When I ask "What is teh PRA minimun ICR for buy-to-lett?"
    Then the answer mentions "125 percent" or "5.5 percent"

  Scenario: Bias-fairness - vulnerable-customer question gets conduct guidance
    Given the UK knowledge base is indexed
    When I ask "How should vulnerable customers in arrears be treated?"
    Then the answer mentions "forbearance" or "Breathing Space" or "vulnerable"

  Scenario: Determinism - same question twice gives same citations
    Given the UK knowledge base is indexed
    When I ask "What is Stage 2 under IFRS 9?" twice
    Then both runs cite the same documents
