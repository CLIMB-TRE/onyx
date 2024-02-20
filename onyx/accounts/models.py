from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator
from utils.fields import LowerCharField
from utils.constraints import conditional_value_required


class Site(models.Model):
    code = LowerCharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)


class User(AbstractUser):
    username = LowerCharField(
        _("username"),
        max_length=100,
        unique=True,
        help_text=_(
            "Required. 100 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[AbstractUser.username_validator, MinLengthValidator(3)],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    site = models.ForeignKey(Site, to_field="code", on_delete=models.CASCADE)
    is_approved = models.BooleanField(default=False)
    creator = models.ForeignKey("User", on_delete=models.PROTECT, null=True)
    is_projectuser = models.BooleanField(default=False)
    project = models.ForeignKey("data.Project", on_delete=models.CASCADE, null=True)

    class Meta:
        constraints = [
            conditional_value_required(
                "is_projectuser",
                True,
                required=["project"],
            )
        ]
