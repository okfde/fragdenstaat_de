from django.conf.urls import include, url

from fragdenstaat_de.theme.urls import urlpatterns as base_urlpatterns

urlpatterns = [
    url(r"^blog/", include("fragdenstaat_de.fds_blog.urls", namespace="blog")),
    url(r"^cms/search/", include("fragdenstaat_de.fds_cms.urls", namespace="fds_cms")),
    url(
        r"^cms/contact/",
        include("fragdenstaat_de.fds_cms.contact", namespace="fds_cms_contact"),
    ),
    url(
        r"^spenden/spende/",
        include("fragdenstaat_de.fds_donation.urls", namespace="fds_donation"),
    ),
    url(r"^crowdfunding/", include("froide_crowdfunding.urls")),
    url(r"^food/", include("froide_food.urls")),
    url(r"^exam/", include("froide_exam.urls")),
] + base_urlpatterns
