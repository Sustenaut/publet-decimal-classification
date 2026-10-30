Feature: A PDC code is a UDC Summary notation, or one extended past a separator
  A PDC class narrower than a UDC class is written as the UDC notation it
  extends, `~`, and a decimal PDC number, one digit per level. UDC notation
  never uses `~`, so a PDC code can never collide with a UDC one.

  Scenario: A UDC Summary class is a PDC code as it stands
    When I check the code "631"
    Then it succeeds
    And stdout says "631	ok	UDC Summary class"

  Scenario: A PDC class names the class it is narrower than in its code
    When I check the code "631.5~12"
    Then it succeeds
    And stdout says "631.5~12	ok	broader 631.5~1"

  Scenario: A first-level PDC class is narrower than its UDC class
    When I check the code "628.9~3"
    Then it succeeds
    And stdout says "628.9~3	ok	broader 628.9"

  Scenario Outline: A code that is neither is refused
    When I check the code "<code>"
    Then it fails
    And stderr says "<reason>"

    Examples:
      | code      | reason                                  |
      | 631.544   | is not a UDC Summary notation           |
      | 999.9~1   | before '~', is not a UDC Summary notation |
      | 631~      | after '~', is not a PDC number          |
      | 631~1.2   | after '~', is not a PDC number          |
      | 631~a     | after '~', is not a PDC number          |

  Scenario: pdc names its version, as a release's identity claim expects
    When I ask pdc for its version
    Then it succeeds
    And stdout is "pdc" and the version in pyproject.toml
