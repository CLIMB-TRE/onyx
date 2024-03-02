from django.db import models
from django.utils.translation import gettext_lazy as _


class StrippedCharField(models.CharField):
    def to_python(self, value):
        if value is None:
            return value

        if not isinstance(value, str):
            value = str(value)

        value = value.strip()
        return super().to_python(value)


class LowerCharField(StrippedCharField):
    def to_python(self, value):
        if value is None:
            return value

        if not isinstance(value, str):
            value = str(value)

        value = value.lower()
        return super().to_python(value)


class UpperCharField(StrippedCharField):
    def to_python(self, value):
        if value is None:
            return value

        if not isinstance(value, str):
            value = str(value)

        value = value.upper()
        return super().to_python(value)


class YearMonthField(models.DateField):
    pass


class ChoiceField(models.TextField):
    pass


class SiteField(models.ForeignKey):
    pass
