Feature: Memo file extraction for PDF JPG JPEG PNG TXT MD
  As a credit analyst
  I want to upload memos in any common format
  So that text is extracted or I get an actionable error

  Scenario: Positive - digital PDF extracts embedded text
    Given a generated digital PDF memo
    When I extract its text
    Then the method is "pdf-text" and "SONIA" is present

  Scenario: Positive - JPG photo extracts text via OCR
    Given a generated JPG memo image
    When I extract its text
    Then the method is "image-ocr" and text is non-empty

  Scenario: Positive - TXT memo extracts directly
    Given a generated TXT memo
    When I extract its text
    Then the method is "text" and "Companies House" is present

  Scenario: Negative - unsupported file type gives actionable error
    Given a file named "memo.xlsx" with fake bytes
    When I extract its text
    Then extraction fails with "unsupported-type"

  Scenario: Negative - blank image gives paste-text guidance
    Given a blank PNG image
    When I extract its text
    Then extraction fails with guidance to "paste" or clearer photo

  Scenario: Edge - JPEG versus JPG extension both handled
    Given a generated JPG memo image saved as ".jpeg"
    When I extract its text
    Then extraction succeeds or reports an OCR message
