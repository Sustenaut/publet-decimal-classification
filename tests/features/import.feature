Feature: The UDC Summary is imported reproducibly as families of subject concepts
  The source file is pinned by checksum. Each labelled class becomes a
  subject concept at its notation, defined in the family under its broader
  class. `tools/publish.py` signs the families and an edition into a new corpus.

  Scenario: The committed import is what the pinned source gives
    Given the program under test is "pdc"
    When I run "pdc import --check"
    Then it succeeds

  Scenario: A class becomes a subject concept matching its UDC URI
    When I look up the concept "631" in the families
    Then the result's "name" is "Agriculture in general"
    And the result's "matches.0.ref" is "http://udcdata.info/050935"
    And the result does not include "sort"
    And the result does not include "kind"
    And the result does not include "relation"

  Scenario: An imported class keeps its broader class from the UDC Summary
    When I look up the class "631" in the import
    Then the result's "uri" is "http://udcdata.info/050935"
    And the result's "broader" is "["631/635"]"

  Scenario: Every imported class is in a committed, signed family
    When I read the committed import
    Then every imported class is defined by its family's object in corpus/objects/, under the CID in data/pdc/cids.json
    And the edition in data/pdc/cids.json is in corpus/objects/ and lists every family there
    And corpus/objects/ holds the PDC steward key's public key object

  Scenario: A source that is not the pinned file is refused
    Given the program under test is "pdc"
    And a scratch directory
    And a file "udc-summary" copied from "data/udc-summary"
    And in the file "udc-summary/udcs.ttl", ""Agriculture in general"@en" is replaced by ""Farming"@en"
    When I run "pdc import --data=udc-summary --out=out"
    Then it fails
    And stderr mentions "not the"

  Scenario: A source whose notation uses the separator is refused
    Given the program under test is "pdc"
    And a scratch directory
    And a file "udc-summary" copied from "data/udc-summary"
    And in the file "udc-summary/udcs.ttl", "skos:notation "631"^^" is replaced by "skos:notation "631~1"^^"
    And the source in "udc-summary" is pinned as it stands
    When I run "pdc import --data=udc-summary --out=out"
    Then it fails
    And stderr mentions "the separator '~' appears in UDC notation"

  Scenario: Every class is defined once, in the family under its broader class
    When I read the committed import
    Then every imported class is in exactly one family, the one under its broader class

  Scenario: The top family holds the two top classes
    When I list the members of the top family
    Then the result is:
      """
      ["-", "----"]
      """

  Scenario: There are 573 families
    When I list the families
    Then the result has 573 families

  Scenario Outline: A special auxiliary head is listed apart from its family's classes
    When I list the <kind> of the family under "<parent>"
    Then the result includes "<code>"
    And the result does not include "<other>"

    Examples:
      | kind        | parent | code    | other   |
      | auxiliaries | 62     | 62-1/-9 | 620     |
      | members     | 62     | 620     | 62-1/-9 |

  Scenario Outline: Each family is in the section of its branch
    When I look up the family under "<parent>"
    Then the result's "section" is "<section>"

    Examples:
      | parent  | section            |
      | 62-1/-9 | special-auxiliaries |
      | (1/9)   | common-auxiliaries |
      | 63      | main               |

  Scenario: A class heading a family is flagged, and no other is
    When I read the committed import
    Then each class has `children` exactly when a family lists it as its parent

  Scenario: Group 1 holds the six heads under "---"
    When I look up group 1
    Then the result is:
      """
      {"number": 1, "heads": ["\"...\"", "(0...)", "(1/9)", "(=...)", "-0...", "=..."]}
      """

  Scenario: The six heads under "---" are the members of its family
    When I list the members of the family under "---"
    Then the result is:
      """
      ["\"...\"", "(0...)", "(1/9)", "(=...)", "-0...", "=..."]
      """

  Scenario: Each family names one grouping, of the groups its branch may use
    When I read the committed import
    Then group 1 holds the members of the family under "---"
    And the grouping of the family under "62" is the common group and that of "62-1/-9"
    And the grouping of the family under "616" adds those of "616-01/-099" to the common group
    And every family's grouping is defined, and every grouping's groups are

  Scenario: The stated counts are what the families make
    When I read the committed import
    Then the counts in families.json agree with the families

  Scenario: An import keeps the numbers of the one before
    Given the program under test is "pdc"
    And a scratch directory
    And a file "out/families.json" holding the committed families with the group numbers reversed
    When I run "pdc import --out=out"
    Then it succeeds
    And each head in "out/families.json" keeps its reversed number

  Scenario: A class that is not under one broader class is refused
    When I group a class with two broader classes into families
    Then it is refused, saying "2 broader classes"

  Scenario: Publishing drives pub through the families, the edition and the publish
    Given a scratch directory
    And a stand-in pub that composes what it is given
    And a key directory "key/.publet"
    And the program under test is "publish.py"
    When I run "publish.py --key=key/.publet --corpus=new --release=0.2.0 --created=2026-11-02T18:00:00Z"
    Then it succeeds
    And the stand-in composed every family and then the edition, each signed with purpose "authored"
    And the stand-in's edition lists every family composed, and "new/pdc-cids.json" names it and every code
    And the file "new/.draft-discards" holds "policy=pub:sha2-256:initpolicy"
    And the file "new/.publet/signing.key" does not exist
    And the file "new/.publet/config" includes "author=pub:sha2-256:steward"
    And the stand-in was asked to publish only after the pin was checked in the repository

  Scenario Outline: Publishing refuses what it should not act on
    Given a scratch directory
    And a stand-in pub that composes what it is given
    And a key directory "key/.publet"
    And a file "taken/README" holding "a corpus already here"
    And the program under test is "publish.py"
    When I run "publish.py --key=<key> --corpus=<corpus> --release=0.2.0 --created=<created>"
    Then it fails
    And stderr mentions "<reason>"
    And the stand-in composed nothing
    And the file "../outside" does not exist

    Examples:
      | corpus     | created              | key         | reason                           |
      | ../outside | 2026-11-02T18:00:00Z | key/.publet | must name one new directory here |
      | a/b        | 2026-11-02T18:00:00Z | key/.publet | must name one new directory here |
      | ..         | 2026-11-02T18:00:00Z | key/.publet | must name one new directory here |
      | taken      | 2026-11-02T18:00:00Z | key/.publet | taken exists                     |
      | new        | yesterday            | key/.publet | must be a UTC time               |
      | new        | 2026-11-02T18:00:00Z | not-a-key   | is not a .publet directory       |

  Scenario: Publishing refuses without pub on PATH
    Given a scratch directory
    And a key directory "key/.publet"
    And no directory on PATH holds "pub"
    And the program under test is "publish.py"
    When I run "publish.py --key=key/.publet --corpus=new --release=0.2.0 --created=2026-11-02T18:00:00Z"
    Then it fails
    And stderr mentions "no `pub` on PATH"

  Scenario: The installed package reads the edition
    Given a scratch directory
    And a file "cids.json" copied from "data/pdc/cids.json"
    When I ask the package for its edition
    Then the result is what the JSON in "cids.json" has at "edition"

  Scenario: The installed package reads each code's family
    Given a scratch directory
    And a file "cids.json" copied from "data/pdc/cids.json"
    When I ask the package for every code's family
    Then the result is what the JSON in "cids.json" has at "classes"
    And the result has 2430 codes

  Scenario: The installed package reads a class for every code
    When I ask the package for its classes
    Then the result has 2430 classes

  Scenario: The installed package reads the families
    When I ask the package for its families
    Then the result has 573 families

  Scenario: Publishing makes one edition of a fresh corpus, signed by the key
    Given a scratch directory
    And a throwaway key "key/.publet" made by a pub that knows families
    And the program under test is "publish.py"
    When I run "publish.py --key=key/.publet --corpus=new --release=0.2.0 --created=2026-11-02T18:00:00Z"
    Then it succeeds
    And the edition of the corpus "new" lists every family by its CID
    And the file "new/.publet/signing.key" does not exist
    And the key's store is unchanged

  Scenario: Publishing refuses a corpus that exists
    Given a scratch directory
    And a throwaway key "key/.publet" made by a pub that knows families
    And a file "new/README" holding "a corpus already here"
    And the program under test is "publish.py"
    When I run "publish.py --key=key/.publet --corpus=new --release=0.2.0 --created=2026-11-02T18:00:00Z"
    Then it fails
    And stderr mentions "exists; the families start a new corpus"
