from django.db import models


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


class PrimaryIDField(UpperCharField):
    pass


class YearMonthField(models.DateField):
    pass


class ChoiceField(models.TextField):
    def __init__(self, **kwargs):
        # Ensures the ModelSerializer validates the field as a choice field
        if "choices" not in kwargs:
            kwargs["choices"] = [("choice", "Choice")]
        super().__init__(**kwargs)


class SiteField(models.ForeignKey):
    pass
