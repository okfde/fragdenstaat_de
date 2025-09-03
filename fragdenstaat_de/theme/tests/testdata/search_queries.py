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
    ("Hunde und Mäuse", ["18"], [["Hund", "Maus", "Hunde", "Mäuse"]]),
    # Umlaut removal leads to "schon" and "schön" being treated as the same word.
    ("schon", ["13"], [["schon", "schön"]]),
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
        ["7", "1", "4", "6"],
        [
            ["Informationsfreiheit"],
            # "Informationen" should probably not match here.
            ["Informationsfreiheitsgesetz", "Informationen"],
            ["Informationsfreiheitssatzung"],
            ["Informations", "Freiheit"],
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
        ["7", "1", "4", "6"],
        [
            ["Informationsfreiheit"],
            ["Informationsfreiheitsgesetz", "Informationen"],
            ["Informationsfreiheitssatzung"],
            ["Informations", "Freiheit"],
        ],
    ),
    (
        "Informationsfreiheitsgesetz",
        ["1"],
        # "Informationen" should probably not match here.
        [["Informationsfreiheitsgesetz", "Informationen"]],
    ),
    (
        "Freiheitsgesetz",
        ["1"],
        [["Informationsfreiheitsgesetz"]],
    ),
    (
        "Freiheit",
        ["7", "4", "6", "1"],
        [
            ["Informationsfreiheit"],
            ["Informationsfreiheitssatzung"],
            ["Freiheit"],
            ["Informationsfreiheitsgesetz"],
        ],
    ),
    ("Gesetz", ["1", "2"], [["Informationsfreiheitsgesetz"], ["Gesetz"]]),
    ("Fußgänger", ["3"], [["Fußgängerübergänge"]]),
    (
        "Übergang",
        ["20", "3"],
        # "über" and "Gang" are detected as matches.
        [["über", "Gang"], ["Fußgängerübergänge"]],
    ),
    ("Güterverkehr", [], []),  # Missing match: "Güterverkehrskonzept"
    (
        "Verkehrskonzept",
        ["5", "19"],
        # "Verkehrsmittel" matches in addition to "Verkehrskonzept".
        [["Güterverkehrskonzept"], ["Verkehrskonzept", "Verkehrsmittel"]],
    ),
    (
        "Verkehrskonzepte",
        ["5", "19"],
        # "Verkehrsmittel" matches in addition to "Verkehrskonzept".
        [["Güterverkehrskonzept"], ["Verkehrskonzept", "Verkehrsmittel"]],
    ),
    # Risk word if decompounding goes wild with detected subtokens "verb" and "tun".
    ("Verbeamtung", ["17"], [["Verbeamtung"]]),
    # "gut" and "guter" match "Gütersloh" because of the strangely working decompounder.
    # "Güterverkehrskonzept" should probably not match in these cases, either.
    (
        "guter",
        ["5", "15", "3"],
        [["Güterverkehrskonzept"], ["gut"], ["Gütersloh", "gut"]],
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
    # --- Tests with special query syntax.
    ("anfrage -ministerium", ["10", "11"], [["Anfrage"], ["Anfrage"]]),
    ("Götersloh~1", ["3"], [["Gütersloh"]]),
    ('"Zugang Informationen"~1', ["1"], [["Zugang zu Informationen"]]),
    (
        "Informations*",
        ["1", "4", "6", "7"],
        [
            ["Informationsfreiheitsgesetz"],
            ["Informationsfreiheitssatzung"],
            ["Informations"],
            ["Informationsfreiheit"],
        ],
    ),
    (
        "Informationsfr*",
        ["1", "4", "7"],
        [
            ["Informationsfreiheitsgesetz"],
            ["Informationsfreiheitssatzung"],
            ["Informationsfreiheit"],
        ],
    ),
    # Prefix search should probably not match in the middle of a word.
    (
        "freih*",
        ["1", "4", "6", "7"],
        [
            ["Informationsfreiheitsgesetz"],
            ["Informationsfreiheitssatzung"],
            ["Freiheit"],
            ["Informationsfreiheit"],
        ],
    ),
    # --- Normal search and exact phrase search combined.
    ('Ministerium "Kleine Anfrage"', ["9"], [["Ministerium", "Kleine Anfrage"]]),
]


# Exact phrase search tests (with quotes).
exact_phrase_search_tests = [
    ("die", ["10", "2", "9", "11", "3"], [["Die"], ["Die"], ["die"], ["die"], ["die"]]),
    ("die Stadt", ["3"], [["die Stadt"]]),
    ("Gesetz", ["1", "2"], [["Informationsfreiheitsgesetz"], ["Gesetz"]]),
    ("Informationsfreiheit", ["7"], [["Informationsfreiheit"]]),
    ("neues Gesetz", ["2"], [["neues Gesetz"]]),
    ("Gesetz neues", [], []),
    ("kleine Anfrage", ["10", "9"], [["Kleine Anfrage"], ["Kleine Anfrage"]]),
    ("kleinen Anfrage", ["11"], [["Kleinen Anfrage"]]),
    ("Hunde und Mäuse", ["18"], [["Hunde und Mäuse"]]),
]
