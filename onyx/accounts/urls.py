from django.urls import path, re_path
from . import views
from knox import views as knox_views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="accounts.register"),
    path("login/", views.LoginView.as_view(), name="knox_login"),
    path("logout/", knox_views.LogoutView.as_view(), name="knox_logout"),
    path("logoutall/", knox_views.LogoutAllView.as_view(), name="knox_logoutall"),
    path("profile/", views.ProfileView.as_view(), name="accounts.profile"),
    path("activity/", views.ActivityView.as_view(), name="accounts.activity"),
    path("waiting/", views.WaitingUsersView.as_view(), name="accounts.waiting"),
    re_path(
        r"^approve/(?P<username>[a-zA-Z0-9_\.\-]*)/$",
        views.ApproveUserView.as_view(),
        name="accounts.approve",
    ),
    path("site/", views.SiteUsersView.as_view(), name="accounts.siteusers"),
    path("all/", views.AllUsersView.as_view(), name="accounts.allusers"),
    re_path(
        r"^projectuser/(?P<project_code>[a-zA-Z_\-]*)/(?P<site_code>[a-zA-Z_\-]*)/(?P<username>[a-zA-Z0-9_\.\-]*)/$",
        views.ProjectUserView.as_view(),
        name="accounts.projectuser",
    ),
]
