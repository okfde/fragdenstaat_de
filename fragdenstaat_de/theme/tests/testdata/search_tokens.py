decompounder_analyzer_tests = [
    ("Information", ["information"]),
    ("Informationsfreiheit", ["informationsfreiheit", "information", "freiheit"]),
    (
        "Informationsfreiheitsgesetz",
        ["informationsfreiheitsgesetz", "information", "freiheit", "gesetz"],
    ),
    ("Gütersloh", ["gutersloh", "gut"]),
    ("die Stadt", ["die", "stadt"]),
    ("der Hund und die Maus", ["der", "hund", "und", "die", "maus"]),
    ("Fußgängerübergänge", ["fussgangerubergang", "fuss", "gang", "uber"]),
    ("Test, Test, 123!", ["test", "test", "123"]),
    ("Güterverkehrskonzept", ["guterverkehrskonzept", "gut", "verkehrs", "konzept"]),
]

text_analyzer_tests = [
    ("Information", ["information"]),
    (
        "Informationsfreiheit",
        ["informationsfreiheit", "informations", "freiheit", "information"],
    ),
    (
        "Informationsfreiheitsgesetz",
        [
            "informationsfreiheitsgesetz",
            "informations",
            "freiheits",
            "gesetz",
            "information",
            "freiheit",
        ],
    ),
    ("Gütersloh", ["gutersloh", "guter", "gut"]),
    ("die Stadt", ["die", "stadt"]),
    ("der Hund und die Maus", ["der", "hund", "und", "die", "maus"]),
    (
        "Fußgängerübergänge",
        ["fussgangerubergange", "fuss", "ganger", "uber", "fussgangerubergang", "gang"],
    ),
    ("Test, Test, 123!", ["test", "test", "123"]),
    (
        "Güterverkehrskonzept",
        ["guterverkehrskonzept", "guter", "verkehrs", "konzept", "gut"],
    ),
]

search_analyzer_tests = [
    ("Gütersloh", ["gutersloh"]),
    ("die Stadt", ["stadt"]),
    ("der Hund und die Maus", ["hund", "maus"]),
]

search_quote_analyzer_tests = [
    ("Gütersloh", ["gutersloh"]),
    ("die Stadt", ["die", "stadt"]),
    ("der Hund und die Maus", ["der", "hund", "und", "die", "maus"]),
]
