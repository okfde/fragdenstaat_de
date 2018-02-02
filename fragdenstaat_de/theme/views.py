# -*- encoding: utf-8 -*-
from django.shortcuts import render

from froide.foirequest.models import FoiRequest
from froide.publicbody.models import PublicBody
from froide.frontpage.models import FeaturedRequest
from froide.helper.cache import cache_anonymous_page


@cache_anonymous_page(15 * 60)
def index(request):
    successful_foi_requests = FoiRequest.published.successful()[:6]
    featured = (FeaturedRequest.objects.all()
                                       .order_by("-timestamp")
                                       .select_related('request',
                                                       'request__public_body'))
    return render(request, 'index.html', {
        'featured': featured[:3],
        'successful_foi_requests': successful_foi_requests,
        'foicount': FoiRequest.objects.get_send_foi_requests().count(),
        'pbcount': PublicBody.objects.get_list().count()
    })


@cache_anonymous_page(30 * 60)
def gesetze_dashboard(request):
    PUBLISHES = {
        'Bundesministerium der Justiz und für Verbraucherschutz': ('<a href="https://www.bmjv.de/SiteGlobals/Forms/Suche/Stellungnahmensuche_Formular.html?nn=7563996&templateQueryString=Nach+Gesetzvorhaben+suchen">ja, seit 2016</a>', 'success'),
        'Bundesministerium für Wirtschaft und Energie': ('teilweise', 'warning'),
    }

    NUMBER_OF_TOP_ORGS = {
        'Auswärtiges Amt': (9, 1),
        'Beauftragte der Bundesregierung für Kultur und Medien': (2, 2),
        'Bundesministerium für Bildung und Forschung': (16, 1),
        'Bundesministerium für Umwelt, Naturschutz, Bau und Reaktorsicherheit': (2, 22),
        'Bundesministerium für Verkehr und digitale Infrastruktur': (2, 13),
        'Bundesministerium für Wirtschaft und Energie': (2, 13),
    }

    TOP_VERBAND = {
        'Bundesministerium der Finanzen': ('Ifo-Institut für Wirtschaftsforschung', 26),
        'Bundesministerium der Justiz und für Verbraucherschutz': ('Deutscher Anwaltverein e. V. (DAV)', 51),
        'Bundesministerium des Innern': ('Evangelische Kirche in Deutschland - EKD', 16),
        'Bundesministerium für Arbeit und Soziales': ('Bundesvereinigung der Deutschen Arbeitgeberverbände', 11),
        'Bundesministerium für Ernährung und Landwirtschaft': ('Deutscher Bauernverband e. V. (DBV)', 13),
        'Bundesministerium für Familie, Senioren, Frauen und Jugend': ('Deutscher Städtetag', 4),
        'Bundesministerium für Gesundheit': ('GKV-Spitzenverband', 10),
    }

    from django.db import models

    pbs = PublicBody.objects.filter(
        informationobject__campaign__slug='stellungnahmen-zu-gesetzentwurfen'
        ).annotate(
            count=models.Count('informationobject'),
            foirequest_count=models.Count('informationobject__foirequest')
        ).distinct()

    for pb in pbs:
        pb.publishes_laws = (('nein', 'danger') if pb.name not in PUBLISHES
                             else PUBLISHES[pb.name])
        pb.top_verband = (None if pb.name not in TOP_VERBAND
                             else TOP_VERBAND[pb.name])
        pb.top_count = (None if pb.name not in NUMBER_OF_TOP_ORGS
                             else NUMBER_OF_TOP_ORGS[pb.name])
        pb.request_made_percent = round(pb.foirequest_count / pb.count * 100)

    embed = request.GET.get('embed', None)

    return render(request, 'campaign/gesetze_dashboard.html', {
        'base': 'simple_base.html' if embed else 'base.html',
        'pbs': pbs
    })
