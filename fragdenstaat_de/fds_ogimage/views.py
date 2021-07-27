from froide.account.views import ProfileView
from froide.foirequest.views import FoiRequestView


class ProfileOGView(ProfileView):
    template_name = "fds_ogimage/profile.html"


class FoiRequestOGView(FoiRequestView):
    template_name = "fds_ogimage/foirequest.html"
