import datetime
import logging
import re
from collections import Counter

from django import forms
from django.utils import timezone

from froide.account.models import UserPreference

logger = logging.getLogger(__name__)

UPPERCASE_LETTERS = re.compile(r"[A-Z]")


def validate_not_too_many_uppercase(name):
    if " " in name:
        return
    if len(UPPERCASE_LETTERS.findall(name)) >= 3:
        raise forms.ValidationError("Zu viele Großbuchstaben im Namen.")


class SignupUserCheckExtra:
    def on_init(self, form):
        pass

    def on_clean(self, form):
        try:
            if "first_name" in form.cleaned_data:
                validate_not_too_many_uppercase(form.cleaned_data["first_name"])
            if "last_name" in form.cleaned_data:
                validate_not_too_many_uppercase(form.cleaned_data["last_name"])
        except forms.ValidationError:
            raise

    def on_save(self, form, user):
        pass


BET_CHOICES = [
    ("bw", "Baden-Württemberg"),
    ("by", "Bayern"),
    ("be", "Berlin"),
    ("bb", "Brandenburg"),
    ("hb", "Bremen"),
    ("hh", "Hamburg"),
    ("he", "Hessen"),
    ("mv", "Mecklenburg-Vorpommern"),
    ("ni", "Niedersachsen"),
    ("nw", "Nordrhein-Westfalen"),
    ("rp", "Rheinland-Pfalz"),
    ("sl", "Saarland"),
    ("sn", "Sachsen"),
    ("st", "Sachsen-Anhalt"),
    ("sh", "Schleswig-Holstein"),
    ("th", "Thüringen"),
]

TIPP_SPIEL_NAME = "fds_meisterschaften_2020_name"


class TippspielForm(forms.Form):
    name = forms.CharField(max_length=50)
    match = forms.IntegerField(min_value=13, max_value=14)
    bet = forms.ChoiceField(choices=BET_CHOICES)

    def clean(self):
        deadline = datetime.datetime(
            2020, 8, 28, 12, 0, 0, tzinfo=timezone.get_current_timezone()
        )
        if timezone.now() >= deadline:
            raise forms.ValidationError("Tipp-Spiel-Runde abgelaufen!")

    def save(self, user):
        UserPreference.objects.update_or_create(
            user=user,
            key=TIPP_SPIEL_NAME,
            defaults={"value": self.cleaned_data["name"]},
        )
        key = "fds_meisterschaften_2020_{}".format(self.cleaned_data["match"])
        UserPreference.objects.update_or_create(
            user=user, key=key, defaults={"value": self.cleaned_data["bet"]}
        )


TOP_COUNT = 20


def calculate_tipp_table(winners, top_count=TOP_COUNT):
    import pandas as pd

    tipper = Counter()
    for match_number, winner in winners.items():
        key = "fds_meisterschaften_2020_{}".format(match_number)
        tipper.update(
            UserPreference.objects.filter(key=key, value=winner).values_list(
                "user_id", flat=True
            )
        )
    df = pd.DataFrame(tipper.items(), columns=["user_id", "points"])
    df["rank"] = df["points"].rank(method="dense", ascending=False).apply(int)
    df = df.sort_values("rank")
    df = df[:top_count]
    names = UserPreference.objects.filter(
        key=TIPP_SPIEL_NAME, user_id__in=list(df["user_id"])
    )
    names = {x.user_id: x.value for x in names}
    df["name"] = df["user_id"].apply(lambda x: names.get(x, "-"))
    return df
