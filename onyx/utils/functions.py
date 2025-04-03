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
    object_type: str | None = None,
    field: str | None = None,
):
    """
    Returns a permission string for a given `app_label`, `action`, `code`, `object_type` and `field`.

    The permission string is in the format:

    `<app_label>.<action>_<code>`

    If `object_type` is provided, the permission string will be in the format:

    `<app_label>.<action>_<code>_<object_type>`

    If `object_type` and `field` are provided, the permission string will be in the format:

    `<app_label>.<action>_<code>_<object_type>__<field>`
    """

    permission = f"{app_label}.{action}_{code}"

    if field and not object_type:
        raise ValueError("If field is provided, object_type must also be provided.")

    if object_type:
        permission += f"_{object_type}"

    if field:
        permission += f"__{field}"

    return permission


def parse_permission(permission: str) -> tuple[str, str, str, str, str]:
    """
    Parses a permission string into its components.

    Returns a tuple containing the `app_label`, `action`, `code`, `object_type` and `field`.
    """

    # TODO: This function could be better... use regex?
    # TODO: Permission forming/parsing is a bit scattered and can probably be consolidated.

    app_label, codename = permission.split(".")
    action_project_object, _, field_path = codename.partition("__")
    action, _, project_object_type = action_project_object.partition("_")
    project, _, object_type = project_object_type.partition("_")

    if not app_label or not action or not project:
        raise ValueError(
            f"Invalid permission string: {permission}. Must begin with '<app_label>.<action>_<project>'"
        )

    if field_path and not object_type:
        raise ValueError(
            f"Invalid permission string: {permission}. If field is provided, object_type must also be provided."
        )

    return app_label, action, project, object_type, field_path


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
