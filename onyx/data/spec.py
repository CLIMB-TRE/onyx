from typing import Any
from rest_framework.serializers import Field
from utils.functions import get_date_input_formats, get_date_output_format
from .serializers import BaseRecordSerializer
from .fields import OnyxField
from .types import Actions, OnyxType


def generate_restrictions(
    field: str,
    onyx_field: OnyxField,
    serializer_field: Field,
    serializer: BaseRecordSerializer,
) -> list[str]:
    # Add additional restrictions
    restrictions = []

    # Add array type
    if onyx_field.onyx_type == OnyxType.ARRAY:
        base_onyx_field = onyx_field.base_onyx_field
        assert base_onyx_field is not None
        restrictions.append(f"Array type: {base_onyx_field.onyx_type.label}")

    # Add date formatting information
    if onyx_field.onyx_type in {OnyxType.DATE, OnyxType.DATETIME}:
        input_format = (
            ", ".join(get_date_input_formats(serializer_field))  # type: ignore
            .replace("%Y", "YYYY")
            .replace("%m", "MM")
            .replace("%d", "DD")
        )
        output_format = (
            get_date_output_format(serializer_field)  # type: ignore
            .replace("%Y", "YYYY")
            .replace("%m", "MM")
            .replace("%d", "DD")
        )
        restrictions.append(f"Input formats: {input_format}")
        restrictions.append(f"Output format: {output_format}")

    # Add max length
    if onyx_field.onyx_type == OnyxType.TEXT and onyx_field.field_instance.max_length:
        restrictions.append(f"Max length: {onyx_field.field_instance.max_length}")

    # Add min and max values
    if onyx_field.onyx_type in {OnyxType.INTEGER, OnyxType.DECIMAL}:
        min_value = serializer_field.min_value  #  type: ignore
        max_value = serializer_field.max_value  #  type: ignore

        # Default min/max values for Django IntegerField
        # https://docs.djangoproject.com/en/5.2/ref/models/fields/#integerfield
        if min_value is not None and min_value > -(2**31):
            restrictions.append(f"Min value: {min_value}")

        if max_value is not None and max_value < (2**31) - 1:
            restrictions.append(f"Max value: {max_value}")

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

    return restrictions


def generate_fields_spec(
    fields_dict: dict,
    onyx_fields: dict[str, OnyxField],
    actions_map: dict[str, str],
    serializer: type[BaseRecordSerializer],
    context: dict[str, Any] | None = None,
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
        context: The context for the serializer.
        prefix: The prefix to use for the field paths.

    Returns:
        The annotated dictionary of fields.
    """

    # Initialize the fields specification
    fields_spec = {}

    # Create an instance of the serializer
    serializer_instance = serializer(context=context)
    assert isinstance(serializer_instance, BaseRecordSerializer)

    # Get the serializer fields to include in the specification
    # These are ordered by the serializer.Meta.fields attribute
    # Append any fields not in the serializer.Meta.fields attribute or OnyxMeta relations
    fields = list(
        field for field in serializer.Meta.fields if field in fields_dict
    ) + list(
        field
        for field in fields_dict
        if field not in serializer.Meta.fields
        and field not in serializer.OnyxMeta.relations
    )

    # Handle serializer fields
    for field in fields:
        # If a prefix is provided, use it to create the field path
        if prefix:
            field_path = f"{prefix}__{field}"
        else:
            field_path = field

        # Get the Onyx field and serializer field
        onyx_field = onyx_fields[field_path]
        serializer_field = serializer_instance.fields[field]

        # Override the field's description from the serializer if it exists
        description = serializer_field.help_text
        if not description:
            description = onyx_field.description

        # If the field is required when is_published = True, override required status
        for (f, v, _), reqs in serializer.OnyxMeta.conditional_value_required.items():
            if f == "is_published" and v and field in reqs:
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
                required = onyx_field.required

        # Generate initial spec for the field
        field_spec = {
            "description": description,
            "type": onyx_field.onyx_type.label,
            "required": required,
            "actions": [
                action.label
                for action in Actions
                if action.label in actions_map[field_path]
            ],
        }

        # Add default value if it exists
        if onyx_field.default is not None:
            field_spec["default"] = onyx_field.default

        # Add choices if the field is a choice field
        if onyx_field.onyx_type == OnyxType.CHOICE:
            field_spec["values"] = sorted(onyx_field.choices)

        # Add primary_id status
        if onyx_field.is_primary_id:
            field_spec["primary_id"] = onyx_field.is_primary_id

        # Add additional restrictions
        restrictions = generate_restrictions(
            field=field,
            onyx_field=onyx_field,
            serializer_field=serializer_field,
            serializer=serializer_instance,
        )
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

        # Get the Onyx field
        onyx_field = onyx_fields[field_path]

        # Generate spec for the field
        fields_spec[field] = {
            "description": onyx_field.description,
            "type": onyx_field.onyx_type.label,
            "required": onyx_field.required,
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
                context=context,
                prefix=field_path,
            ),
        }

    return fields_spec
