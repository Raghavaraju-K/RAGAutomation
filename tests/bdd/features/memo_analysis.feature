Feature: UK memo analysis checklist
  As a credit analyst
  I want my memo scored against UK banking standards
  So that gaps are found before committee

  Scenario: Positive - strong UK memo is ready for review
    Given a strong UK memo text
    When I analyse the memo
    Then the verdict is "READY FOR REVIEW"
    And all 8 checklist rows have check score and status
    And standards evidence cites UK documents

  Scenario: Positive - PDF memo analysed end to end
    Given a generated digital PDF memo
    When I analyse the memo file
    Then a verdict is returned with overall score at least 0.5

  Scenario: Negative - weak memo is flagged before committee
    Given a weak memo text missing debenture and covenants
    When I analyse the memo
    Then the verdict is "NEEDS WORK BEFORE COMMITTEE"
    And at least 3 gaps are reported

  Scenario: Negative - empty memo returns an error
    Given an empty memo text
    When I analyse the memo
    Then an error is returned

  Scenario: Edge - missing file returns an error
    Given a path to a memo file that does not exist
    When I analyse the memo file
    Then an error is returned
