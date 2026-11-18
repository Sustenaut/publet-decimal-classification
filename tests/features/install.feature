Feature: pip installs the PDC with its data
  The package carries the generated data as `pdc.data`, so `pdc` and the
  Python API work from an installed copy, with no checkout beside it.

  Scenario: An installed pdc checks codes and reads its own data
    Given a scratch directory
    And the package installed with pip into a fresh environment, first on PATH
    When I run "pdc code 631.5~12"
    Then it succeeds
    And it prints:
      """
      631.5~12	ok	broader 631.5~1
      """
    And the installed package reads every imported class and its CID from its own data
    And the installed pdc names the version in pyproject.toml
