from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions


class ObjectNotFound(exceptions.NotFound):
    default_detail = _("Object not found.")


class RecordIDNotFound(exceptions.NotFound):
    default_detail = _("Record ID not found.")


class AnalysisIdNotFound(exceptions.NotFound):
    default_detail = _("Analysis ID not found.")


class IdentifierNotFound(exceptions.NotFound):
    default_detail = _("Identifier not found.")
