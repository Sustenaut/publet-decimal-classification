Feature: pip installs the PDC with its data
  The package carries the generated data as `pdc.data`, so `pdc` and the
  Python API work from an installed copy, with no checkout beside it.

  Scenario: An installed pdc checks codes and reads its own data
    Given the package installed with pip into a fresh environment
    When I check the code "631.5~12" with the installed pdc
    Then it succeeds
    And stdout says "631.5~12	ok	broader 631.5~1"
    And the installed package reads every imported class and its CID from its own data
    And the installed pdc names the version in pyproject.toml
