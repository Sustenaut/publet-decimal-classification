Feature: The UDC Summary is imported reproducibly as subject concepts
  The source file is pinned by checksum. Each labelled class becomes a
  subject concept at its notation, placed under its broader classes.

  Scenario: The committed import is what the pinned source gives
    When I check the import
    Then it succeeds

  Scenario: A class becomes a subject concept matching its UDC URI
    Then the imported class "631" is a concept named "Agriculture in general"
    And the imported class "631" matches "http://udcdata.info/"
    And the imported class "631" is under "631/635"

  Scenario: Every imported class is a committed, signed object
    Then every imported class has a concept object in corpus/objects/ under its CID in data/pdc/cids.json
    And corpus/objects/ holds the PDC steward key's public key object

  Scenario: A source that is not the pinned file is refused
    Given a copy of the source with one class relabelled
    When I import the copy
    Then it fails
    And stderr says "not the"

  Scenario: A source whose notation uses the separator is refused
    Given a copy of the source with the notation "631~1" pinned as it stands
    When I import the copy
    Then it fails
    And stderr says "the separator '~' appears in UDC notation"
