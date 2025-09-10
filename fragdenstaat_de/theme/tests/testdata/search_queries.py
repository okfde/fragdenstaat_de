# Test cases for search with the following format:
# (query, matching documents_ids, matching highlightest text snippets per document)
search_tests = [
    # --- Basic tests of different spellings and cases.
    ("test", ["8"], [["Test", "TEST", "Tést"]]),
    ("TEST", ["8"], [["Test", "TEST", "Tést"]]),
    ("tést", ["8"], [["Test", "TEST", "Tést"]]),
    # --- Stopwords.
    ("die", [], []),
    ("die Stadt", ["4", "3"], [["Stadt"], ["Stadt"]]),
    # --- Different inflection forms and umlaut.
    ("Dokument", ["12"], [["Dokument"]]),
    ("Dokumente", ["12"], [["Dokument"]]),
    ("Dokumenten", ["12"], [["Dokument"]]),
    ("Dokuments", ["12"], [["Dokument"]]),
    ("Begriff", ["12"], [["Begriffe"]]),
    ("Begriffe", ["12"], [["Begriffe"]]),
    ("Begriffen", ["12"], [["Begriffe"]]),
    ("Begriffes", ["12"], [["Begriffe"]]),
    ("Begriffs", ["12"], [["Begriffe"]]),
    ("Fußgängerübergang", ["3"], [["Fußgängerübergänge"]]),
    ("Gütersloh", ["3"], [["Gütersloh"]]),
    ("Gütersloher", ["3"], [["Gütersloh"]]),
    ("Kürbis", ["14"], [["Kürbisse"]]),
    ("Lehrkraft", ["17"], [["Lehrkräften"]]),
    # Umlaut removal leads to "schon" and "schön" being treated as the same word.
    (
        "schon",
        ["13"],
        [["schon", "schön"]],
    ),
    ("schön", ["13"], [["schon", "schön"]]),
    # These are cases that currently do not work as expected. They could be fixed with a better stemmer/lemmatizer.
    ("Auto", [], []),  # Missing match: "Autos"
    ("Nudel", [], []),  # Missing match: "Nudeln"
    ("Ministerien", [], []),  # Missing match: "Ministerium"
    # --- Compound words and their components.
    (
        "Information",
        ["1", "7", "4", "6"],
        [
            ["Informationsfreiheitsgesetz", "Informationen"],
            ["Informationsfreiheit"],
            ["Informationsfreiheitssatzung"],
            ["Informations"],
        ],
    ),
    (
        "Informationsfreiheit",
        # Missing match: "Informations-Freiheit"
        ["1", "4", "7"],
        [
            ["Informationsfreiheitsgesetz"],
            ["Informationsfreiheitssatzung"],
            ["Informationsfreiheit"],
        ],
    ),
    (
        "Information Freiheit",
        ["7", "1", "4", "6"],
        [
            ["Informationsfreiheit"],
            ["Informationsfreiheitsgesetz", "Informationen"],
            ["Informationsfreiheitssatzung"],
            ["Informations", "Freiheit"],
        ],
    ),
    (
        "Informations-Freiheit",
        # Missing match: "Informations-Freiheit"
        ["1", "4", "7"],
        [
            ["Informationsfreiheitsgesetz"],
            ["Informationsfreiheitssatzung"],
            ["Informationsfreiheit"],
        ],
    ),
    ("Informationsfreiheitsgesetz", ["1"], [["Informationsfreiheitsgesetz"]]),
    (
        "Freiheitsgesetz",
        # Not a match, but would be nice: "Informationsfreiheitsgesetz"
        [],
        [],
    ),
    ("Gesetz", ["1", "2"], [["Informationsfreiheitsgesetz"], ["Gesetz"]]),
    ("Fußgänger", ["3"], [["Fußgängerübergänge"]]),
    ("Übergang", [], []),  # Missing match: "Fußgängerübergänge"
    ("Güterverkehr", ["5"], [["Güterverkehrskonzept"]]),
    ("Verkehrskonzept", [], []),  # Missing match: "Güterverkehrskonzept
    # Risk word if decompounding goes wild with detected subtokens "verb" and "tun".
    ("Verbeamtung", ["17"], [["Verbeamtung"]]),
    # "gut" and "guter" match "Gütersloh" because of the strangely working decompounder.
    # "Güterverkehrskonzept" should probably not match in these cases, either.
    (
        "guter",
        ["5", "3", "15"],
        [["Güterverkehrskonzept"], ["Gütersloh", "gut"], ["gut"]],
    ),
    (
        "gut",
        ["5", "15", "3"],
        [["Güterverkehrskonzept"], ["gut"], ["Gütersloh", "gut"]],
    ),
    ("gut stadt", ["3"], [["Gütersloh", "gut", "Stadt"]]),
    (
        "gut | städte",
        ["3", "5", "4", "15"],
        [["Gütersloh", "gut", "Stadt"], ["Güterverkehrskonzept"], ["Stadt"], ["gut"]],
    ),
    # --- Multi-word queries.
    ("neues Gesetz", ["2"], [["neues", "Gesetz"]]),
    ("Gesetz neues", ["2"], [["neues", "Gesetz"]]),
    (
        "neues | Gesetz",
        ["2", "1", "3"],
        [["neues", "Gesetz"], ["Informationsfreiheitsgesetz"], ["neue"]],
    ),
    (
        "kleine Anfrage",
        ["10", "9", "11"],
        [["Kleine", "Anfrage"], ["Kleine", "Anfrage"], ["Kleinen", "Anfrage"]],
    ),
    ("anfrage -ministerium", ["10", "11"], [["Anfrage"], ["Anfrage"]]),
    # --- Normal search and exact phrase search combined.
    ('Ministerium "Kleine Anfrage"', ["9"], [["Ministerium", "Kleine Anfrage"]]),
]


# Test cases for testing the analyzer directly.
# As no decompounder is used here, subwords are not found.
analyzer_search_tests = [
    ("Informationsfreiheit", ["7"], [["Informationsfreiheit"]]),
    ("Fußgänger", [], []),
    ("Güterverkehr", [], []),
]


# Exact phrase search tests (with quotes).
exact_phrase_search_tests = [
    ("die", ["10", "2", "9", "11", "3"], [["Die"], ["Die"], ["die"], ["die"], ["die"]]),
    ("die Stadt", ["3"], [["die Stadt"]]),
    ("Gesetz", ["1", "2"], [["Informationsfreiheitsgesetz"], ["Gesetz"]]),
    ("neues Gesetz", ["2"], [["neues Gesetz"]]),
    ("Gesetz neues", [], []),
    ("kleine Anfrage", ["10", "9"], [["Kleine Anfrage"], ["Kleine Anfrage"]]),
    ("kleinen Anfrage", ["11"], [["Kleinen Anfrage"]]),
]
