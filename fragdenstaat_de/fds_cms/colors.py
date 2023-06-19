from django.utils.translation import gettext_lazy as _

BACKGROUND = (
    [
        ("", _("None")),
        ("callout", _("Callout")),
        ("highlight", _("Highlight")),
        ("body", _("Default Body")),
        ("body-secondary", _("Body Secondary")),
        ("body-tertiary", _("Body Tertiary")),
        ("dark-subtle", _("Dark Subtle")),
        ("light-subtle", _("Light Subtle")),
        ("primary", _("Primary")),
        ("primary-subtle", _("Primary Subtle")),
        ("secondary", _("Secondary")),
        ("secondary-subtle", _("Secondary Subtle")),
        ("info", _("Info")),
        ("info-subtle", _("Info Subtle")),
        ("success", _("Success")),
        ("success-subtle", _("Success Subtle")),
        ("warning", _("Warning")),
        ("warning-subtle", _("Warning Subtle")),
        ("danger", _("Danger")),
        ("danger-subtle", _("Danger Subtle")),
        ("purple", _("Purple")),
        ("pink", _("Pink")),
        ("yellow", _("Yellow")),
        ("cyan", _("Cyan")),
        ("gray", _("Gray")),
        ("gray-dark", _("Gray Dark")),
        ("white", _("White")),
        ("light", _("Light")),
        ("dark", _("Dark")),
        ("transparent", _("Transparent")),
    ]
    + [("gray-{}".format(i), "Gray {}".format(i)) for i in range(100, 1000, 100)]
    + [
        ("blue-10", _("Blue 10")),
        ("blue-20", _("Blue 20")),
        ("blue-30", _("Blue 30")),
    ]
    + [("blue-{}".format(i), "Blue {}".format(i)) for i in range(100, 900, 100)]
    + [("yellow-{}".format(i), "Yellow {}".format(i)) for i in range(100, 400, 100)]
)


# css variable names vary slightly from the class names...
def get_css_color_variable(color: str):
    if color == "body":
        color = "body-bg"
    elif color in ("body-secondary", "body-tertiary"):
        color = color.replace("body-", "")
        color += "-bg"
    elif color.endswith("-subtle"):
        color = color.replace("-subtle", "-bg-subtle")

    return "--bs-" + color


BACKDROP = (("", _("None")), ("50", "50 %"), ("75", "75 %"))
