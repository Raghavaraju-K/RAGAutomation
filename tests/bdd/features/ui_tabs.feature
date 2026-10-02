Feature: Streamlit UI for UK credit memo analysis
  As a credit analyst
  I want a working UI with memo upload, Q&A, KB view, eval and feedback
  So that I can test the app without a browser script

  Scenario: Positive - all five tabs render
    Given the Streamlit app loads
    Then 5 tabs render named Analyse My Memo, Ask UK Standards, Knowledge Base, Evaluation Dashboard and Fine-tune

  Scenario: Positive - memo tab has uploader and paste box
    Given the Streamlit app loads
    When I open the "Analyse My Memo" tab
    Then a memo file uploader is visible
    And a paste-text box is visible

  Scenario: Positive - ask tab has question box and Top-K slider
    Given the Streamlit app loads
    When I open the "Ask UK Standards" tab
    Then a question box is visible
    And a Top-K control is visible

  Scenario: Positive - knowledge base tab lists UK-only documents
    Given the Streamlit app loads
    When I open the "Knowledge Base (UK only)" tab
    Then only UK standards documents are listed

  Scenario: Positive - evaluation dashboard shows quality gates
    Given the Streamlit app loads with an evaluation report
    When I open the "Evaluation Dashboard" tab
    Then Recall@5 is at least 0.90
    And Faithfulness is at least 0.90
    And Hallucination is at most 0.05

  Scenario: Negative - dashboard without report still loads
    Given the Streamlit app loads
    When I open the "Evaluation Dashboard" tab
    Then the app still loads without crashing

  Scenario: Edge - app loads with zero exceptions
    Given the Streamlit app loads
    Then no exception is raised
