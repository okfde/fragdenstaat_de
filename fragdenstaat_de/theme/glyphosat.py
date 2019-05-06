import re

import requests

from froide.foirequest.models import FoiAttachment

try:
    from glyphosat import convert_images
except ImportError:
    convert_images = lambda x: None


USERNAME_RE = re.compile(r'Ihr Benutzername lautet: ([\w\.]+@fragdenstaat.de)')
PASSWORD_RE = re.compile(r'Ihr Kennwort lautet: (\w+)')
FILENAME = 'bfr-stellungnahme-bad.pdf'


def get_glyphosat_document(message):
    if any(a.name == FILENAME for a in message.attachments):
        return message.get_absolute_url()

    text = message.plaintext
    username_match = USERNAME_RE.search(text)
    password_match = PASSWORD_RE.search(text)
    if not username_match or not password_match:
        return

    username = username_match.group(1)
    password = password_match.group(1)

    BASE_URL = 'https://dokumente.bfr.bund.de/glypo/'
    session = requests.Session()
    response = session.get(BASE_URL)
    response = session.post(BASE_URL, {
        'email': username,
        'token': password,
        'confirm-notes': '1'
    })
    response

    # IMAGE_URL = 'https://dokumente.bfr.bund.de/glypo/page?page=glypo-{}.jpg'
    # for i in range(6):
    #     session.get(IMAGE_URL.format(i))

    convert_images(session)

    FoiAttachment.objects.create(
        belongs_to=message,
        file='foi/59/7f/f0/597ff06bb9d18a0b578e10aece646841f136c8ec903e29b4c2ac953323950b9a.pdf',
        name=FILENAME,
        size=1322710,
        filetype='application/pdf',
        can_approve=False,
        approved=False,
    )
    return message.get_absolute_url()
