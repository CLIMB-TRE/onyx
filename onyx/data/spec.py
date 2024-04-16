from typing import Any
from django.db import models
from utils.functions import get_date_input_formats, get_date_output_format
from .serializers import BaseRecordSerializer
from .fields import OnyxField
from .actions import Actions
from .types import OnyxType


def generate_fields_spec(
    fields_dict: dict,
    onyx_fields: dict[str, OnyxField],
    actions_map: dict[str, str],
    serializer: type[BaseRecordSerializer],
    prefix: str | None = None,
) -> dict[str, Any]:
    """
    Generate the fields specification for a project from the provided `fields_dict`, `onyx_fields`, `actions_map`, and `serializer`.

    For each field, this information includes:
    * The front-facing type name
    * Required status
    * Available actions
    * Choices
    * Default value
    * Additional restrictions (e.g. max length, optional value groups)

    Args:
        fields_dict: The dictionary containing fields to annotate.
        onyx_fields: The dictionary of `OnyxField` objects to use for annotation.
        actions_map: The dictionary of field paths to their available actions.
        serializer: The serializer to use for annotation.
        prefix: The prefix to use for the field paths.

    Returns:
        The annotated dictionary of fields.
    """

    fields_spec = {}

    serializer_instance = serializer()
    assert isinstance(serializer_instance, BaseRecordSerializer)

    # Handle serializer fields
    serializer_fields = serializer_instance.get_fields()
    for field in serializer.Meta.fields:
        # Skip fields that are not in the fields_dict
        if field not in fields_dict:
            continue

        # If a prefix is provided, use it to create the field path
        if prefix:
            field_path = f"{prefix}__{field}"
        else:
            field_path = field

        # Get the field's OnyxType and field instance
        onyx_type = onyx_fields[field_path].onyx_type
        field_instance = onyx_fields[field_path].field_instance

        # Override the field's description from the serializer if it exists
        description = serializer_fields[field].help_text
        if not description:
            description = onyx_fields[field_path].description

        # If the field is required when is_published = True, override required status
        for (f, v, _), reqs in serializer.OnyxMeta.conditional_value_required.items():
            if f == "is_published" and v == True and field in reqs:
                required = True
                break
        else:
            # published_date doesn't have serializer is_published validation
            # this is because published_date gets added after validation, on save
            # but it does have the constraint so it is required on publish
            # TODO: Add published_date addition to serializer so it can be validated?
            if field == "published_date":
                required = True
            else:
                required = onyx_fields[field_path].required

        # Generate initial spec for the field
        field_spec = {
            "description": description,
            "type": onyx_type.label,
            "required": required,
            "actions": [
                action.label
                for action in Actions
                if action.label in actions_map[field_path]
            ],
        }

        # Add default value if it exists
        if field_instance.default != models.NOT_PROVIDED:
            field_spec["default"] = field_instance.default

        # Add choices if the field is a choice field
        if onyx_type == OnyxType.CHOICE and onyx_fields[field_path].choices:
            field_spec["values"] = sorted(onyx_fields[field_path].choices)

        # Add additional restrictions
        restrictions = []

        # Add date formatting information
        if onyx_type in {OnyxType.DATE, OnyxType.DATETIME}:
            input_format = (
                ", ".join(get_date_input_formats(serializer_fields[field]))
                .replace("%Y", "YYYY")
                .replace("%m", "MM")
                .replace("%d", "DD")
            )
            output_format = (
                get_date_output_format(serializer_fields[field])
                .replace("%Y", "YYYY")
                .replace("%m", "MM")
                .replace("%d", "DD")
            )
            restrictions.append(f"Input formats: {input_format}")
            restrictions.append(f"Output format: {output_format}")

        # Add max length
        if onyx_type == OnyxType.TEXT and field_instance.max_length:
            restrictions.append(f"Max length: {field_instance.max_length}")

        # Add optional_value_groups
        for optional_value_group in serializer.OnyxMeta.optional_value_groups:
            if field in optional_value_group:
                restrictions.append(
                    f"At least one required: {', '.join(optional_value_group)}"
                )

        # Add conditional_required
        for f, reqs in serializer.OnyxMeta.conditional_required.items():
            if field == f:
                restrictions.append(f"Requires: {', '.join(reqs)}")

        # Add conditional_value_required
        for (f, v, _), reqs in serializer.OnyxMeta.conditional_value_required.items():
            if f != "is_published" and field in reqs:
                restrictions.append(f"Required when {f} is: {v}")

        if restrictions:
            field_spec["restrictions"] = restrictions

        # Add the field spec to the fields spec
        fields_spec[field] = field_spec

    # Handle serializer relations
    for field, nested_serializer in serializer.OnyxMeta.relations.items():
        # Skip fields that are not in the fields_dict
        if field not in fields_dict:
            continue

        # If a prefix is provided, use it to create the field path
        if prefix:
            field_path = f"{prefix}__{field}"
        else:
            field_path = field

        # Get the field's OnyxType and field instance
        onyx_type = onyx_fields[field_path].onyx_type
        field_instance = onyx_fields[field_path].field_instance

        # Generate spec for the field
        fields_spec[field] = {
            "description": onyx_fields[field_path].description,
            "type": onyx_type.label,
            "required": onyx_fields[field_path].required,
            "actions": [
                action.label
                for action in Actions
                if action.label in actions_map[field_path]
            ],
            # Recursively generate fields spec for the nested serializer
            "fields": generate_fields_spec(
                fields_dict=fields_dict[field],
                onyx_fields=onyx_fields,
                actions_map=actions_map,
                serializer=nested_serializer,
                prefix=field_path,
            ),
        }

    return fields_spec
