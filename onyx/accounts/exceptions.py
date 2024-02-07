from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions


class ProjectNotFound(exceptions.NotFound):
    default_detail = _("Project not found.")


class UserNotFound(exceptions.NotFound):
    default_detail = _("User not found.")


class SiteNotFound(exceptions.NotFound):
    default_detail = _("Site not found.")
