from froide.account.views import ProfileView


class ProfileOGView(ProfileView):
    template_name = 'fds_ogimage/profile.html'
