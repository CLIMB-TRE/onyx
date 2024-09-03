from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions


class ClimbIDNotFound(exceptions.NotFound):
    default_detail = _("CLIMB ID not found.")


class IdentifierNotFound(exceptions.NotFound):
    default_detail = _("Identifier not found.")


class AnalysisIdNotFound(exceptions.NotFound):
    default_detail = _("Analysis ID not found.")
