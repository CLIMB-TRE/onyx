from typing import Any
from functools import cached_property
from django.db import models
from django.contrib.postgres.fields import ArrayField
from rest_framework import exceptions
from utils.fields import (
    StrippedCharField,
    LowerCharField,
    UpperCharField,
    ChoiceField,
    SiteField,
)
from utils.functions import get_suggestions, get_permission, parse_permission
from accounts.models import User
from .models import Choice, Project, PrimaryRecord
from .types import Actions, Objects, OnyxLookup, OnyxType


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
        "value",
        "base_onyx_field",
        "many_to_many",
    )

    def __init__(
        self,
        project: Project,
        field_model: type[models.Model],
        field_path: str,
        lookup: str,
        allow_lookup: bool = False,
        value: Any = None,
        is_base_field: bool = False,
        many_to_many: bool = False,
    ):
        self.project = project
        self.field_model = field_model
        self.field_path = field_path
        self.field_name = self.field_path.split("__")[-1]

        if is_base_field:
            base_field_instance = self.field_model._meta.get_field(
                self.field_name
            ).base_field  # type: ignore
            assert isinstance(base_field_instance, models.Field)
            self.field_instance = base_field_instance
        else:
            self.field_instance = self.field_model._meta.get_field(self.field_name)

        self.field_type = type(self.field_instance)
        self.base_onyx_field = None
        self.many_to_many = many_to_many

        # Determine the OnyxType for the field
        if self.field_type in {
            models.UUIDField,
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

        elif self.field_type in {models.IntegerField, models.BigIntegerField}:
            self.onyx_type = OnyxType.INTEGER

        elif self.field_type == models.FloatField:
            self.onyx_type = OnyxType.DECIMAL

        elif self.field_type == models.DateField:
            self.onyx_type = OnyxType.DATE

        elif self.field_type == models.DateTimeField:
            self.onyx_type = OnyxType.DATETIME

        elif self.field_type == models.BooleanField:
            self.onyx_type = OnyxType.BOOLEAN

        elif self.field_instance.many_to_many:
            self.onyx_type = OnyxType.IDENTIFIERS

        elif self.field_instance.is_relation:
            self.onyx_type = OnyxType.RELATION

        elif self.field_type == ArrayField:
            self.onyx_type = OnyxType.ARRAY
            self.base_onyx_field = OnyxField(
                project=project,
                field_model=field_model,
                field_path=field_path,
                lookup="",
                allow_lookup=False,
                is_base_field=True,
            )

        elif self.field_type == models.JSONField:
            self.onyx_type = OnyxType.STRUCTURE

        else:
            raise NotImplementedError(
                f"Field {self.field_type} did not match an OnyxType."
            )

        # Determine the field description
        if (
            # many-to-one and one-to-many
            isinstance(self.field_instance, models.ManyToOneRel)
            # many-to-many
            or isinstance(self.field_instance, models.ManyToManyRel)
        ):
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
        if allow_lookup:
            # If lookups are allowed, check it is valid
            if lookup not in self.onyx_type.lookups:
                suggestions = get_suggestions(
                    lookup,
                    options=self.onyx_type.lookups,
                    cutoff=0,
                    message_prefix="Invalid lookup.",
                )

                raise exceptions.ValidationError(suggestions)
        else:
            # If lookups are not allowed, ensure one was not provided
            if lookup:
                raise exceptions.ValidationError("Lookups are not allowed.")

        self.lookup = lookup
        self.value = value


class FieldHandler:
    """
    Class that does the following for a given `project`, `action`, `object_type`, `model` and `user`:

    - Resolves fields (converts field strings into `OnyxField` objects).
    - Checks whether the `user` has permission to perform the `action` on the resolved fields.
    - Provides functions for retrieving fields that can be actioned on.
    """

    project: Project
    action: Actions
    object_type: Objects
    model: type[PrimaryRecord]
    user: User

    def __init__(
        self,
        project: Project,
        action: Actions,
        object_type: Objects,
        model: type[PrimaryRecord],
        user: User,
    ) -> None:
        self.project = project
        self.action = action
        self.object_type = object_type
        self.model = model
        self.user = user

    @cached_property
    def fields(self) -> list[str]:
        """
        All fields that the user can perform the handler's action on.

        Returns:
            The list of fields that the user can action on.
        """

        action_fields = []
        for permission in self.user.get_all_permissions():
            app_label, action, project, object_type, field = parse_permission(
                permission
            )
            if (
                app_label == self.project.content_type.app_label
                and action == self.action.label
                and project == self.project.code
                and object_type == self.object_type.label
                and field
            ):
                action_fields.append(field)

        return action_fields

    def field_suggestions(self, field, message_prefix=None) -> str:
        """
        Get a suggestions message for an unknown/invalid field.

        The suggestions are based on the fields that the user can action on.

        Args:
            field: The unknown/invalid field to get suggestions for.
            message_prefix: The message prefix to use. Defaults to "This field is unknown."

        Returns:
            The suggestions message.
        """

        if not message_prefix:
            message_prefix = "This field is unknown."

        suggestions = get_suggestions(
            field,
            options=self.fields,
            n=1,
            message_prefix=message_prefix,
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
            app_label=self.project.content_type.app_label,
            action=Actions.ACCESS.label,
            code=self.project.code,
            object_type=self.object_type.label,
            field=onyx_field.field_path,
        )

        if not self.user.has_perm(field_access_permission):
            raise exceptions.ValidationError(
                self.field_suggestions(onyx_field.field_path)
            )

        # Check the user's permission to perform action on the field
        # If the user does not have permission, tell them it is not allowed
        field_action_permission = get_permission(
            app_label=self.project.content_type.app_label,
            action=self.action.label,
            code=self.project.code,
            object_type=self.object_type.label,
            field=onyx_field.field_path,
        )

        if not self.user.has_perm(field_action_permission):
            raise exceptions.ValidationError(
                self.field_suggestions(
                    onyx_field.field_path,
                    f"You cannot {self.action.description} this field.",
                )
            )

    def resolve_field(self, field: str, allow_lookup=False) -> OnyxField:
        """
        Resolve a provided `field`, determining which model it comes from.

        This information is stored in an `OnyxField` object.

        Args:
            field: The field to resolve.
            allow_lookup: Whether to allow a lookup to be specified.

        Returns:
            The resolved `OnyxField` object.
        """

        # Base model for the project
        current_model = self.model
        model_fields = {x.name: x for x in current_model._meta.get_fields()}

        # Split the field into its individual components
        # If there are multiple components, these should specify
        # a chain of relations through multiple models
        components = field.split("__")
        many_to_many = False
        field_path = ""
        lookup = ""
        for i, component in enumerate(components):
            # If the current component is not known on the current model
            # Then add to unknown fields
            if component not in model_fields:
                raise exceptions.ValidationError(self.field_suggestions(field))

            # Corresponding field instance for the component
            component_instance = model_fields[component]
            field_path = "__".join(components[: i + 1])
            lookup = "__".join(components[i + 1 :])

            if lookup in OnyxLookup.lookups():
                break

            if component_instance.is_relation:
                # The field's 'lookup' may be remaining components in a relation
                # Move on to them
                current_model = component_instance.related_model
                assert current_model is not None

                # Mark OnyxField as many-to-many if one of the components is a ManyToManyField
                if component_instance.many_to_many:
                    many_to_many = True

                model_fields = {x.name: x for x in current_model._meta.get_fields()}
                next_component = components[i + 1] if i + 1 < len(components) else ""

                if next_component in model_fields:
                    continue

            if len(components[i + 1 :]) > 1:
                raise exceptions.ValidationError(self.field_suggestions(field))
            else:
                suggestions = get_suggestions(
                    lookup,
                    options=list(OnyxLookup.lookups()),
                    n=1,
                    message_prefix="This lookup is unknown.",
                )
                raise exceptions.ValidationError(suggestions)

        # Instantiate OnyxField object
        onyx_field = OnyxField(
            project=self.project,
            field_model=current_model,
            field_path=field_path,
            lookup=lookup,
            allow_lookup=allow_lookup,
            many_to_many=many_to_many,
        )

        # Check that the user can perform the given action on this field
        # Raises a ValidationError if this is not the case
        self.check_field_permissions(onyx_field)

        # Return OnyxField object
        return onyx_field

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
