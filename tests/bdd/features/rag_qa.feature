Feature: UK credit-memo RAG question answering
  As a credit analyst
  I want grounded answers from the UK-standards knowledge base
  So that every answer cites UK sources and meets quality gates

  Scenario: Positive - PRA buy-to-let ICR question is answered with citation
    Given the UK knowledge base is indexed
    When I ask "What is the PRA minimum ICR and stressed rate for buy-to-let?"
    Then the answer mentions "125 percent" or "5.5 percent"
    And the answer cites a UK standards document
    And the latency is under 3 seconds

  Scenario: Positive - UK pricing reference rate is SONIA
    Given the UK knowledge base is indexed
    When I ask "What reference rate replaces SOFR for UK pricing?"
    Then the answer mentions "SONIA"

  Scenario: Positive - IFRS 9 Stage 2 is lifetime ECL
    Given the UK knowledge base is indexed
    When I ask "What is Stage 2 under IFRS 9?"
    Then the answer mentions "Stage 2" or "Stage 1"

  Scenario: Negative - gibberish question does not hallucinate a UK rule
    Given the UK knowledge base is indexed
    When I ask "zzzqqq blorpt flimflam wobble 99999"
    Then the answer does not invent "FCA Handbook section 999"

  Scenario: Edge - empty question returns a safe fallback
    Given the UK knowledge base is indexed
    When I ask an empty question
    Then an answer is still returned with citations or a safe fallback

  Scenario: Metamorphic - paraphrase gives consistent answer
    Given the UK knowledge base is indexed
    When I ask "What is the PRA minimum ICR and stressed rate for buy-to-let?"
    And I ask "PRA minimum ICR stressed rate BTL?"
    Then both answers mention "125 percent" or "5.5 percent"
