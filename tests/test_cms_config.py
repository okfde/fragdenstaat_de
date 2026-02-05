import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("configuration", ["Gegenrechtsschutz", "Ubf"])
@pytest.mark.django_db
def test_cms_configuration(configuration):
    # Need to run subprocess to properly run Django's
    # import machinery
    env = {**os.environ, "DJANGO_MEDIA_ROOT": str(Path("./media").resolve())}

    completed_process = subprocess.run(
        [
            "python",
            "manage.py",
            "check",
            "--settings",
            "fragdenstaat_de.settings.production",
            "--configuration",
            configuration,
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert (
        completed_process.returncode == 0
    ), f"Configuration {configuration} failed check: {completed_process.stdout} {completed_process.stderr}"
