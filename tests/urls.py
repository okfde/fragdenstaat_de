from django.urls import include, path

from fragdenstaat_de.theme.urls import urlpatterns as base_urlpatterns

urlpatterns = [
    path("blog/", include("fragdenstaat_de.fds_blog.urls", namespace="blog")),
    path("cms/search/", include("fragdenstaat_de.fds_cms.urls", namespace="fds_cms")),
    path(
        "cms/contact/",
        include("fragdenstaat_de.fds_cms.contact", namespace="fds_cms_contact"),
    ),
    path(
        "spenden/spende/",
        include("fragdenstaat_de.fds_donation.urls", namespace="fds_donation"),
    ),
    path("crowdfunding/", include("froide_crowdfunding.urls")),
    path("food/", include("froide_food.urls")),
    path("exam/", include("froide_exam.urls")),
] + base_urlpatterns
