Feature: The UDC Summary is imported reproducibly as families of subject concepts
  The source file is pinned by checksum. Each labelled class becomes a
  subject concept at its notation, defined in the family under its broader
  class. `tools/publish.py` signs the families and an edition into a new corpus.

  Scenario: The committed import is what the pinned source gives
    When I check the import
    Then it succeeds

  Scenario: A class becomes a subject concept matching its UDC URI
    Then the imported class "631" is a concept named "Agriculture in general"
    And the imported class "631" matches "http://udcdata.info/"
    And the imported class "631" is under "631/635"

  Scenario: Every imported class is in a committed, signed family
    Then every imported class is defined by its family's object in corpus/objects/, under the CID in data/pdc/cids.json
    And the edition in data/pdc/cids.json is in corpus/objects/ and lists every family there
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

  Scenario: Every class is defined once, in the family under its broader class
    Then every imported class is in exactly one family, the one under its broader class
    And the top family holds "-" and "----"
    And there are 573 families

  Scenario: A special auxiliary head is listed apart from its family's classes
    Then the family under "62" lists "62-1/-9" as an auxiliary and "620" as a member
    And the family under "62-1/-9" is in the section "special-auxiliaries"
    And the family under "(1/9)" is in the section "common-auxiliaries"
    And the family under "63" is in the section "main"

  Scenario: A class heading a family is flagged, and no other is
    Then each class has `children` exactly when a family lists it as its parent

  Scenario: Each family names one grouping, of the groups its branch may use
    Then group 1 holds the six heads under "---"
    And the grouping of the family under "62" is the common group and that of "62-1/-9"
    And the grouping of the family under "616" adds those of "616-01/-099" to the common group
    And every family's grouping is defined, and every grouping's groups are

  Scenario: The stated counts are what the families make
    Then the counts in families.json agree with the families

  Scenario: An import keeps the numbers of the one before
    Given the families with the group numbers reversed
    When I import over them
    Then it succeeds
    And each head keeps its reversed number

  Scenario: A class that is not under one broader class is refused
    Then a class with two broader classes is refused

  Scenario: Publishing drives pub through the families, the edition and the publish
    Given a stand-in pub and a key directory
    When I publish to a new corpus with the stand-in pub
    Then it succeeds
    And the stand-in composed every family and then the edition, each signed with purpose "authored"
    And the stand-in's edition lists every family composed, and pdc-cids.json names it and every code
    And the new corpus lists the init policy in .draft-discards, and its signing link is gone
    And the stand-in was asked to publish only after the pin was checked in the repository

  Scenario Outline: Publishing refuses what it should not act on
    Given a stand-in pub and a key directory
    When I publish with <argument> set to <value> with the stand-in pub
    Then it fails
    And stderr says "<reason>"
    And nothing was composed

    Examples:
      | argument  | value                | reason                                   |
      | --corpus  | ../outside           | must name one new directory here         |
      | --corpus  | a/b                  | must name one new directory here         |
      | --corpus  | ..                   | must name one new directory here         |
      | --corpus  | taken                | taken exists                             |
      | --created | yesterday            | must be a UTC time                       |
      | --key     | not-a-key            | is not a .publet directory               |

  Scenario: Publishing refuses without pub on PATH
    Given a stand-in pub and a key directory
    When I publish to a new corpus with no pub on PATH
    Then it fails
    And stderr says "no `pub` on PATH"

  Scenario: The installed package reads the edition and each code's family
    Then pdc.edition() is the edition in data/pdc/cids.json, and pdc.cids() gives every code's family
    And pdc.family_data() has 573 families

  Scenario: Publishing makes one edition of a fresh corpus, signed by the key
    Given a throwaway key and a pub that knows families
    When I publish to a new corpus
    Then it succeeds
    And the corpus's edition lists every family by its CID
    And the corpus's signing link is gone and the key's store is unchanged

  Scenario: Publishing refuses a corpus that exists
    Given a throwaway key and a pub that knows families
    When I publish to a corpus that exists
    Then it fails
    And stderr says "exists; the families start a new corpus"
