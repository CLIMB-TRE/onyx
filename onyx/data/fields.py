from typing import Any
from django.db import models
from rest_framework import exceptions
from utils.fields import (
    StrippedCharField,
    LowerCharField,
    UpperCharField,
    ChoiceField,
    YearMonthField,
    SiteField,
)
from utils.functions import get_suggestions, get_permission, parse_permission
from accounts.models import User
from .models import Choice, Project, ProjectRecord
from .types import OnyxType, ALL_LOOKUPS
from .actions import Actions


class OnyxField:
    """
    Class for storing information on a field (and lookup) requested by a user.
    """

    __slots__ = (
        "project",
        "field_model",
        "field_path",
        "field_name",
        "field_instance",
        "field_type",
        "onyx_type",
        "required",
        "description",
        "choices",
        "lookup",
    )

    def __init__(
        self,
        project: str,
        field_model: type[models.Model],
        field_path: str,
        lookup: str,
        allow_lookup: bool = False,
    ):
        self.project = project
        self.field_model = field_model
        self.field_path = field_path
        self.field_name = self.field_path.split("__")[-1]
        self.field_instance = self.field_model._meta.get_field(self.field_name)
        self.field_type = type(self.field_instance)

        # Determine the OnyxType for the field
        if self.field_type in {
            models.CharField,
            models.TextField,
            StrippedCharField,
            LowerCharField,
            UpperCharField,
        }:
            self.onyx_type = OnyxType.TEXT

        elif self.field_type in {ChoiceField, SiteField}:
            self.onyx_type = OnyxType.CHOICE
            self.choices = Choice.objects.filter(
                project=self.project,
                field=self.field_name,
            ).values_list("choice", flat=True)

        elif self.field_type == models.IntegerField:
            self.onyx_type = OnyxType.INTEGER

        elif self.field_type == models.FloatField:
            self.onyx_type = OnyxType.DECIMAL

        elif self.field_type == YearMonthField:
            self.onyx_type = OnyxType.DATE_YYYY_MM

        elif self.field_type == models.DateField:
            self.onyx_type = OnyxType.DATE_YYYY_MM_DD

        elif self.field_type == models.DateTimeField:
            self.onyx_type = OnyxType.DATETIME

        elif self.field_type == models.BooleanField:
            self.onyx_type = OnyxType.BOOLEAN

        elif self.field_instance.is_relation:
            self.onyx_type = OnyxType.RELATION

        else:
            raise NotImplementedError(
                f"Field {self.field_type} did not match an OnyxType."
            )

        # Determine the field description
        if isinstance(self.field_instance, models.ManyToOneRel):
            self.description = self.field_instance.field.help_text
        else:
            self.description = self.field_instance.help_text

        # Determine the field's required status
        if self.onyx_type == OnyxType.TEXT or self.onyx_type == OnyxType.CHOICE:
            self.required = (
                not self.field_instance.blank
                and self.field_instance.default == models.NOT_PROVIDED
            )
        else:
            self.required = (
                not self.field_instance.null
            ) and self.field_instance.default == models.NOT_PROVIDED

        # Validate the lookup
        if not allow_lookup and lookup:
            raise exceptions.ValidationError("Lookups are not allowed.")

        if allow_lookup and lookup not in self.onyx_type.lookups:
            suggestions = get_suggestions(
                lookup,
                options=self.onyx_type.lookups,
                cutoff=0,
                message_prefix="Invalid lookup.",
            )

            raise exceptions.ValidationError(suggestions)

        self.lookup = lookup


class FieldHandler:
    """
    Class that does the following for a given project, action and user:

    - Provide functions for retrieving fields that can be actioned on.
    - Resolves fields (converts field strings into `OnyxField` objects).
    - Checks whether the user has permission to action on the resolved fields.
    """

    __slots__ = "code", "model", "app_label", "action", "user", "fields"

    def __init__(
        self,
        project: Project,
        action: str,
        user: User,
    ) -> None:
        self.code = project.code
        model = project.content_type.model_class()
        assert model is not None
        assert issubclass(model, ProjectRecord)
        self.model = model
        self.app_label = project.content_type.app_label
        self.action = action
        self.user = user
        self.fields = None

    def get_fields(
        self,
    ) -> list[str]:
        """
        Get all fields that can be actioned on.

        Returns:
            The list of fields that the user can action on.
        """

        # If fields have not been cached, retrieve them
        if self.fields is None:
            fields = []

            for permission in self.user.get_all_permissions():
                _, action, project, field = parse_permission(permission)

                if action == self.action and project == self.code and field:
                    fields.append(field)

            self.fields = fields

        return self.fields

    def unknown_field_suggestions(self, field) -> str:
        """
        Get a suggestions message for an unknown field.

        The suggestions are based on the fields that the user can action on.

        Args:
            field: The unknown field.

        Returns:
            The suggestions message.
        """

        suggestions = get_suggestions(
            field,
            options=self.get_fields(),
            message_prefix="This field is unknown.",
        )

        return suggestions

    def check_field_permissions(self, onyx_field: OnyxField):
        """
        Check whether the user can perform the action on the field.

        Args:
            onyx_field: The `OnyxField` object to check user permissions for.
        """

        # TODO: Refactor this to use model name rather than project code?

        # Check the user's permission to access the field
        # If the user does not have permission, tell them it is unknown
        field_access_permission = get_permission(
            app_label=self.app_label,
            action="access",
            code=self.code,
            field=onyx_field.field_path,
        )

        if not self.user.has_perm(field_access_permission):
            raise exceptions.ValidationError(
                self.unknown_field_suggestions(onyx_field.field_path)
            )

        # Check the user's permission to perform action on the field
        # If the user does not have permission, tell them it is not allowed
        field_action_permission = get_permission(
            app_label=self.app_label,
            action=self.action,
            code=self.code,
            field=onyx_field.field_path,
        )

        if not self.user.has_perm(field_action_permission):
            raise exceptions.ValidationError(f"You cannot {self.action} this field.")

    def resolve_field(
        self,
        field: str,
        allow_lookup=False,
    ) -> OnyxField:
        """
        Resolve a provided `field`, determining which model it comes from.

        This information is stored in an `OnyxField` object.

        Args:
            field: The field to resolve.
            allow_lookup: Whether to allow a lookup to be specified.

        Returns:
            The resolved `OnyxField` object.
        """

        # Check for trailing underscore
        # This is required because if a field ends in "__"
        # Splitting will result in some funky stuff
        if field.endswith("_"):
            raise exceptions.ValidationError(self.unknown_field_suggestions(field))

        # Base model for the project
        current_model = self.model
        model_fields = {x.name: x for x in current_model._meta.get_fields()}

        # Split the field into its individual components
        # If there are multiple components, these should specify
        # a chain of relations through multiple models
        components = field.split("__")
        for i, component in enumerate(components):
            # If the current component is not known on the current model
            # Then add to unknown fields
            if component not in model_fields:
                raise exceptions.ValidationError(self.unknown_field_suggestions(field))

            # Corresponding field instance for the component
            component_instance = model_fields[component]
            field_path = "__".join(components[: i + 1])
            lookup = "__".join(components[i + 1 :])

            if lookup in ALL_LOOKUPS:
                # The field is valid, and the lookup is not sus
                # So we attempt to instantiate the field instance
                # This could fail if the lookup is not allowed for the given field

                onyx_field = OnyxField(
                    project=self.code,
                    field_model=current_model,
                    field_path=field_path,
                    lookup=lookup,
                    allow_lookup=allow_lookup,
                )

                # Check that the user can perform the given action on this field
                # Raises a ValidationError if this is not the case
                self.check_field_permissions(onyx_field)

                # Return OnyxField object
                return onyx_field

            elif component_instance.is_relation:
                # The field's 'lookup' may be remaining components in a relation
                # Move on to them
                current_model = component_instance.related_model
                assert current_model is not None
                model_fields = {x.name: x for x in current_model._meta.get_fields()}

            else:
                # Otherwise, it is unknown
                break

        raise exceptions.ValidationError(self.unknown_field_suggestions(field))

    def resolve_fields(
        self,
        fields: list[str],
        allow_lookup=False,
    ) -> dict[str, OnyxField]:
        """
        Resolves provided `fields`, determining which models they come from.

        This information is stored in `OnyxField` objects.

        Args:
            fields: The fields to resolve.
            allow_lookup: Whether to allow a lookup to be specified.

        Returns:
            Dictionary mapping input fields to `OnyxField` objects.
        """

        errors = {}
        resolved = {}

        # Resolve each field
        for field in fields:
            try:
                resolved[field] = self.resolve_field(field, allow_lookup=allow_lookup)
            except exceptions.ValidationError as e:
                errors[field] = [e.args[0]]

        if errors:
            raise exceptions.ValidationError(errors)

        return resolved


def generate_fields_spec(
    fields_dict: dict,
    onyx_fields: dict[str, OnyxField],
    actions_map: dict[str, str],
    serializer,  # TODO: Can't type this as it's a circular import
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

    # Handle serializer fields
    serializer_fields = serializer().get_fields()
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
        for (f, v, d), reqs in serializer.OnyxMeta.conditional_value_required.items():
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
                action.value
                for action in Actions
                if action.value in actions_map[field_path]
            ],
        }

        # Add default value if it exists
        if field_instance.default != models.NOT_PROVIDED:
            field_spec["default"] = field_instance.default

        # Add choices if the field is a choice field
        if onyx_type == OnyxType.CHOICE and onyx_fields[field_path].choices:
            field_spec["values"] = onyx_fields[field_path].choices

        # Add additional restrictions
        restrictions = []
        if onyx_type == OnyxType.TEXT and field_instance.max_length:
            restrictions.append(f"Max length: {field_instance.max_length}")

        for optional_value_group in serializer.OnyxMeta.optional_value_groups:
            if field in optional_value_group:
                restrictions.append(
                    f"At least one required: {', '.join(optional_value_group)}"
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

        # Get the field's OnyxType and field instance
        onyx_type = onyx_fields[field_path].onyx_type
        field_instance = onyx_fields[field_path].field_instance

        # Generate spec for the field
        fields_spec[field] = {
            "description": onyx_fields[field_path].description,
            "type": onyx_type.label,
            "required": onyx_fields[field_path].required,
            "actions": [
                action.value
                for action in Actions
                if action.value in actions_map[field_path]
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


# TODO: This function feels very hacky.
# A lack of type-checking is required on obj in order for request.data to pass.
# Which does make me wonder: is this robust against whatever could be provided through request.data?
# E.g. how sure are we that all 'fields' have been flattened from obj?
def flatten_fields(obj) -> list[str]:
    """
    Flatten a JSON-like `obj` into a list of dunderised keys.

    Args:
        obj: The JSON-like object to flatten.

    Returns:
        The flattened list of dunderised keys.
    """

    dunders = []
    if isinstance(obj, dict):
        for key, item in obj.items():
            # TODO: An ugly but effective fix until I come up with a more elegant solution
            # Basically just want to prevent any dunder separators in keys
            # Long-term would be nice to not need the flatten_fields function, and check perms recursively
            if "__" in key:
                raise exceptions.ValidationError(
                    {
                        "detail": "Field names in request body cannot contain '__' separator."
                    }
                )
            prefix = key
            values = flatten_fields(item)

            if values:
                for v in values:
                    dunders.append(f"{prefix}__{v}")
            else:
                dunders.append(prefix)
    elif isinstance(obj, list):
        for item in obj:
            values = flatten_fields(item)

            for v in values:
                dunders.append(v)
    else:
        return []

    return list(set(dunders))


def unflatten_fields(
    fields: list[str],
) -> dict[str, Any]:
    """
    Unflatten `fields` by splitting on double underscores to form a nested dictionary.

    Args:
        fields: The list of fields to unflatten.

    Returns:
        The unflattened nested dictionary.
    """

    fields_dict = {}

    for field in fields:
        field_pieces = field.split("__")

        if field_pieces:
            current_dict = fields_dict

            for piece in field_pieces:
                if not piece:
                    # Ignore empty strings
                    # These come from permissions where there is no field attached
                    # So there is no __ to split on
                    break

                current_dict.setdefault(piece, {})
                current_dict = current_dict[piece]

    return fields_dict


def include_exclude_fields(
    fields: list[str],
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[str]:
    """
    Filters `fields` to only include/exclude those specified in `include`/`exclude`.

    Args:
        fields: The list of fields to filter.
        include: The list of fields to include. If None, all fields are included.
        exclude: The list of fields to exclude. If None, no fields are excluded.

    Returns:
        The filtered list of fields.
    """

    if include:
        # Include fields that match or are connected by a double underscore to any of the provided inclusion values
        fields = [
            field
            for field in fields
            if any(field == inc or field.startswith(inc + "__") for inc in include)
        ]

    if exclude:
        # Exclude fields that match or are connected by a double underscore to any of the provided exclusion values
        fields = [
            field
            for field in fields
            if not any(field == exc or field.startswith(exc + "__") for exc in exclude)
        ]

    return fields
