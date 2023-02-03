from froide_govplan.views import GovPlanDetailView, GovPlanSectionDetailView

from froide.account.views import ProfileView
from froide.foirequest.views import FoiRequestView


class ProfileOGView(ProfileView):
    template_name = "fds_ogimage/profile.html"


class FoiRequestOGView(FoiRequestView):
    template_name = "fds_ogimage/foirequest.html"


class GovPlanSectionDetailOGView(GovPlanSectionDetailView):
    template_name = "fds_ogimage/govplan_section.html"


class GovPlanDetailOGView(GovPlanDetailView):
    template_name = "fds_ogimage/govplan_plan.html"
