import difflib
import pydantic
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings


def get_suggestions(
    unknown: str,
    options: list[str],
    n=3,
    cutoff=0.4,
    message_prefix: str | None = None,
) -> str:
    """
    Performs a case-insensitive comparison of an `unknown` against a list of `options`.

    Returns a message containing the suggestions.
    """

    options_map = {option.lower().strip(): option for option in options}

    close_matches = difflib.get_close_matches(
        word=unknown.lower().strip(),
        possibilities=options_map.keys(),
        n=n,
        cutoff=cutoff,
    )

    suggestions = [options_map[close_match] for close_match in close_matches]

    if message_prefix:
        message = message_prefix
    else:
        message = ""

    if suggestions:
        message += (
            f"{' ' if message else ''}Perhaps you meant: {', '.join(suggestions)}"
        )

    return message


def get_permission(
    app_label: str,
    action: str,
    code: str,
    field: str | None = None,
):
    """
    Returns a permission string for a given `app_label`, `action`, `code`, and `field`.

    The permission string is in the format:

    `<app_label>.<action>_<code>`

    If `field` is provided, the permission string will be in the format:

    `<app_label>.<action>_<code>__<field>`
    """

    if field:
        return f"{app_label}.{action}_{code}__{field}"
    else:
        return f"{app_label}.{action}_{code}"


def parse_permission(permission: str) -> tuple[str, str, str, str]:
    """
    Parses a permission string into its components.

    Returns a tuple containing the `app_label`, `action`, `code`, and `field`.
    """

    app_label, codename = permission.split(".")
    action_project, _, field_path = codename.partition("__")
    action, project = action_project.split("_")

    return app_label, action, project, field_path


def strtobool(val):
    """
    Convert a string representation of truth to True or False.

    True values are 'y', 'yes', 't', 'true', 'on', and '1'.

    False values are 'n', 'no', 'f', 'false', 'off', and '0'.

    Raises ValueError if 'val' is anything else.
    """

    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"Invalid truth value: {val}")


def get_date_input_formats(
    field: serializers.DateField | serializers.DateTimeField,
) -> list[str]:
    """
    Returns the input formats for a given date serializer field.
    """

    if isinstance(field, serializers.DateField):
        input_formats = getattr(field, "input_formats", api_settings.DATE_INPUT_FORMATS)
    elif isinstance(field, serializers.DateTimeField):
        input_formats = getattr(
            field, "input_formats", api_settings.DATETIME_INPUT_FORMATS
        )
    else:
        raise ValueError(f"Invalid serializer field type: {type(field)}")

    assert isinstance(input_formats, list)
    return input_formats


def get_date_output_format(
    field: serializers.DateField | serializers.DateTimeField,
) -> str:
    """
    Returns the output format for a given date serializer field.
    """

    if isinstance(field, serializers.DateField):
        output_format = getattr(field, "format", api_settings.DATE_FORMAT)
    elif isinstance(field, serializers.DateTimeField):
        output_format = getattr(field, "format", api_settings.DATETIME_FORMAT)
    else:
        raise ValueError(f"Invalid serializer field type: {type(field)}")

    assert isinstance(output_format, str)
    return output_format


def pydantic_to_drf_error(
    e: pydantic.ValidationError,
) -> ValidationError:
    """
    Transform pydantic ValidationError into DRF ValidationError.
    """

    errors = {}

    for error in e.errors(
        include_url=False, include_context=False, include_input=False
    ):
        errors.setdefault("non_field_errors", []).append(error["msg"])

    for name, errs in errors.items():
        errors[name] = list(set(errs))

    return ValidationError(errors)
