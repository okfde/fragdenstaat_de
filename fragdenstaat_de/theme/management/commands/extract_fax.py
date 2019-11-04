import re

from django.core.management.base import BaseCommand

import phonenumbers

from froide.publicbody.models import PublicBody

FAX_RE = re.compile(r'(?:Tele)?[fF]ax(?:nummer|nr)?\.?(?:\(\w+\))?:?\s*(\(?\+?[\[\]– \t\d\-\(\)/\.]+)', re.M)
POST_FAX_RE = re.compile(r'(\(?\+?[\[\]– \t\d\-\(\)/\.]+)\s*\((?:Tele)?[fF]ax(?:nummer|nr)?\.?\)', re.M)


class Command(BaseCommand):
    help = "Extract fax"

    def handle(self, *args, **options):
        for pb in PublicBody.objects.filter(fax='').exclude(contact=''):
            match = FAX_RE.search(pb.contact)
            if match is None:
                continue
            # print(pb.id)
            if not match.group(1).strip():
                continue
            number = None
            while True:
                try:
                    number = phonenumbers.parse(match.group(1).strip(), 'DE')
                    break
                except phonenumbers.phonenumberutil.NumberParseException:
                    if match.group(1).startswith(')'):
                        match = POST_FAX_RE.search(pb.contact)
                    else:
                        print('Bad number:@%s@' % repr(match.group(1)), pb.contact)
                        break
            if number is None:
                continue
            if not phonenumbers.is_possible_number(number):
                print('impossible', match.group(1), '|', pb.contact, '|', pb.id)
                continue
            if not phonenumbers.is_valid_number(number):
                print('invalid', match.group(1), '|', pb.contact, '|', pb.id)
                continue
            fax_number = phonenumbers.format_number(number,
                  phonenumbers.PhoneNumberFormat.E164)
            pb.fax = fax_number
            pb.save()
