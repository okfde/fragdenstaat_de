decompounder_analyzer_tests = [
    ("Information", ["information"]),
    ("Informationsfreiheit", ["informationsfreiheit", "informations", "freiheit"]),
    (
        "Informationsfreiheitsgesetz",
        ["informationsfreiheitsgesetz", "informations", "freiheits", "gesetz"],
    ),
    ("Gütersloh", ["gütersloh", "güter"]),
    ("die Stadt", ["die", "stadt"]),
    ("der Hund und die Maus", ["der", "hund", "und", "die", "maus"]),
    ("Fußgängerübergang", ["fußgängerübergang", "fuß", "gänger", "über", "gang"]),
    # For some reason, the second "gang" is missing here.
    ("Fußgängerübergänge", ["fußgängerübergänge", "fuß", "gänger", "über"]),
    ("Test, Test, 123!", ["test", "test", "123"]),
    ("Güterverkehrskonzept", ["güterverkehrskonzept", "güter", "verkehrs", "konzept"]),
]

text_analyzer_tests = [
    ("Information", ["information"]),
    (
        "Informationsfreiheit",
        ["informationsfreiheit", "information", "freiheit"],
    ),
    (
        "Informationsfreiheitsgesetz",
        [
            "informationsfreiheitsgesetz",
            "information",
            "freiheit",
            "gesetz",
        ],
    ),
    ("Gütersloh", ["gütersloh", "gutersloh", "gut"]),
    ("die Stadt", ["die", "stadt"]),
    ("der Hund und die Maus", ["der", "hund", "und", "die", "maus"]),
    ("Hunde und Mäuse", ["hunde", "hund", "und", "mäuse", "maus"]),
    (
        "Fußgängerübergang",
        [
            "fußgängerübergang",
            "fussgangerubergang",
            "fuss",
            "gang",
            "uber",
        ],
    ),
    (
        "Fußgängerübergänge",
        [
            "fußgängerübergänge",
            "fussgangerubergang",
            "fuss",
            "gang",
            "uber",
            # For some reason, the second "gang" is missing here.
        ],
    ),
    ("Test, Test, 123!", ["test", "test", "123"]),
    (
        "Güterverkehrskonzept",
        [
            "güterverkehrskonzept",
            "guterverkehrskonzept",
            "gut",
            "verkehrs",  # Should be "verkehr".
            "konzept",
        ],
    ),
    ("Freiheitsgesetz", ["freiheitsgesetz", "freiheit", "gesetz"]),
    ("kleinen Anfrage", ["kleinen", "klein", "anfrage", "anfrag"]),
    # Example of weird decompounding.
    (
        "Verbändebeteiligung",
        ["verbändebeteiligung", "verbandebeteiligung", "band", "teil"],
    ),
    # Example of false stemming + weird decompounding.
    ("Schülerinnen", ["schülerinnen", "schulerinn", "rinn"]),
]

search_analyzer_tests = [
    ("Gütersloh", ["gutersloh"]),
    ("die Stadt", ["stadt"]),
    ("der Hund und die Maus", ["hund", "maus"]),
    ("Hunde und Mäuse", ["hund", "maus"]),
    ("Freiheitsgesetz", ["freiheitsgesetz"]),
    ("kleine Anfrage", ["klein", "anfrag"]),
]

search_quote_analyzer_tests = [
    ("Test TEST Tést", ["test", "test", "tést"]),
    ("Gütersloh", ["gütersloh"]),
    ("die Stadt", ["die", "stadt"]),
    ("der Hund und die Maus", ["der", "hund", "und", "die", "maus"]),
    ("Freiheits gesetz", ["freiheits", "gesetz"]),
]
