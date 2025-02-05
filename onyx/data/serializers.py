from __future__ import annotations
import hashlib
from typing import Any
from django.db import transaction, DatabaseError, models
from rest_framework import serializers, exceptions
from accounts.models import User
from utils.defaults import CurrentUserSiteDefault, CurrentProjectDefault
from utils.fieldserializers import DateField, SiteField, StructureField
from utils.functions import get_date_output_format
from . import validators
from .types import OnyxType
from .fields import OnyxField
from .models import Project, Anonymiser, Analysis


# Mapping of OnyxType to Django REST Framework serializer field
# TODO: Currently not possible to initialise with nested date and nested array fields
# Solution would be to have serializer field instances attached to OnyxField objects
FIELDS = {
    OnyxType.TEXT: serializers.CharField,
    OnyxType.CHOICE: serializers.CharField,
    OnyxType.INTEGER: serializers.IntegerField,
    OnyxType.DECIMAL: serializers.FloatField,
    OnyxType.DATE: lambda format: DateField(format=format),
    OnyxType.DATETIME: lambda format: serializers.DateTimeField(format=format),
    OnyxType.BOOLEAN: serializers.BooleanField,
    OnyxType.ARRAY: lambda child: serializers.ListField(child=child),
    OnyxType.STRUCTURE: serializers.JSONField,
}


class HistoryDiffSerializer(serializers.Serializer):
    """
    Serializer for tracked field changes.
    """

    field = serializers.CharField()
    type = serializers.CharField()

    def __init__(
        self,
        *args,
        serializer_cls: type[PrimaryRecordSerializer],
        onyx_field: OnyxField,
        show_values: bool,
        **kwargs,
    ):
        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        serlializer_instance = serializer_cls()
        assert isinstance(serlializer_instance, PrimaryRecordSerializer)
        serializer_fields = serlializer_instance.get_fields()

        if not show_values:
            self.fields["from"] = serializers.CharField()
            self.fields["to"] = serializers.CharField()
        elif onyx_field.onyx_type in {OnyxType.DATE, OnyxType.DATETIME}:
            output_format = get_date_output_format(
                serializer_fields[onyx_field.field_name]
            )
            self.fields["from"] = FIELDS[onyx_field.onyx_type](format=output_format)
            self.fields["to"] = FIELDS[onyx_field.onyx_type](format=output_format)
        elif onyx_field.onyx_type == OnyxType.ARRAY:
            base_onyx_field = onyx_field.base_onyx_field
            assert base_onyx_field is not None
            self.fields["from"] = FIELDS[onyx_field.onyx_type](
                child=FIELDS[base_onyx_field.onyx_type]()
            )
            self.fields["to"] = FIELDS[onyx_field.onyx_type](
                child=FIELDS[base_onyx_field.onyx_type]()
            )
        else:
            self.fields["from"] = FIELDS[onyx_field.onyx_type]()
            self.fields["to"] = FIELDS[onyx_field.onyx_type]()


class IdentifierSerializer(serializers.Serializer):
    """
    Serializer for input to the `data.project.identify` endpoint.
    """

    site = SiteField(default=CurrentUserSiteDefault())
    value = serializers.CharField()


class SummarySerializer(serializers.Serializer):
    """
    Serializer for multi-field count aggregates.
    """

    def __init__(
        self,
        *args,
        serializer_cls: type[PrimaryRecordSerializer],
        onyx_fields: dict[str, OnyxField],
        count_name: str,
        **kwargs,
    ):
        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        serlializer_instance = serializer_cls()
        assert isinstance(serlializer_instance, PrimaryRecordSerializer)
        serializer_fields = serlializer_instance.get_fields()

        for field_name, onyx_field in onyx_fields.items():
            if onyx_field.onyx_type in {OnyxType.DATE, OnyxType.DATETIME}:
                self.fields[field_name] = FIELDS[onyx_field.onyx_type](
                    format=get_date_output_format(serializer_fields[field_name])
                )
            elif onyx_field.onyx_type == OnyxType.ARRAY:
                base_onyx_field = onyx_field.base_onyx_field
                assert base_onyx_field is not None
                self.fields[field_name] = FIELDS[onyx_field.onyx_type](
                    child=FIELDS[base_onyx_field.onyx_type]()
                )
            else:
                self.fields[field_name] = FIELDS[onyx_field.onyx_type]()

        self.fields[count_name] = serializers.IntegerField()


# https://www.django-rest-framework.org/api-guide/serializers/#dynamically-modifying-fields
class BaseRecordSerializer(serializers.ModelSerializer):
    """
    Base serializer for all project data.
    """

    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), default=serializers.CurrentUserDefault()
    )

    def __init__(self, *args, fields: dict[str, Any] | None = None, **kwargs):
        """
        Initialise the serializer.

        The serializer takes an optional `fields` parameter that controls which fields are serialized.

        To serialize relations, these must be configured using the `OnyxMeta` on a `BaseRecordSerializer`.

        Relations should not be deserialized using a `BaseRecordSerializer`, rather through a `SerializerNode`.
        """

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        # NOTE: The fields argument should be used ONLY for viewing data
        if fields is not None:
            allowed = []
            relations = {}

            # Add each provided field to the 'allowed' list
            # If a field is nested, also add it to the 'relations' dict
            for field, nested in fields.items():
                allowed.append(field)

                if nested:
                    relations[field] = nested

            # Initialise serializers for relations
            for field, nested in relations.items():
                relation_serializer = self.OnyxMeta.relations.get(field)

                if relation_serializer:
                    relation_options = self.OnyxMeta.relation_options.get(field, {})

                    # Set allow_null to be opposite of required
                    # I.e. required = True means allow_null = False
                    # and required = False means allow_null = True
                    if relation_options.get("required"):
                        relation_options["allow_null"] = not relation_options[
                            "required"
                        ]

                    # Initialise the serializer
                    self.fields[field] = relation_serializer(
                        fields=nested,
                        **relation_options,
                    )

            # Drop any fields that are not specified in the fields argument.
            allowed = set(allowed)
            existing = set(self.fields)

            for field in existing - allowed:
                self.fields.pop(field)

    def validate(self, data):
        """
        Custom object-level validation, configured using the `OnyxMeta` on a `BaseRecordSerializer`.
        """

        errors = {}

        validators.validate_identifiers(
            errors=errors,
            data=data,
            identifiers=self.OnyxMeta.identifiers,
        )

        if (not self.instance) and self.partial:
            # We only get to here if a serializer was initialised with no instance and partial = True.
            # This only happens when we create the serializer for validating just the identifiers.
            # In this case, we don't want to apply the other object-level validation.
            pass
        else:
            validators.validate_optional_value_groups(
                errors=errors,
                data=data,
                groups=self.OnyxMeta.optional_value_groups,
                instance=self.instance,
            )

            validators.validate_orderings(
                errors=errors,
                data=data,
                orderings=self.OnyxMeta.orderings,
                instance=self.instance,
            )

            validators.validate_choice_constraints(
                errors=errors,
                data=data,
                choice_constraints=self.OnyxMeta.choice_constraints,
                project=self.context["project"],
                instance=self.instance,
            )

            validators.validate_non_futures(
                errors=errors,
                data=data,
                non_futures=self.OnyxMeta.non_futures,
            )

            validators.validate_conditional_required(
                errors=errors,
                data=data,
                conditional_required=self.OnyxMeta.conditional_required,
                instance=self.instance,
            )

            validators.validate_conditional_value_required(
                errors=errors,
                data=data,
                conditional_value_required=self.OnyxMeta.conditional_value_required,
                instance=self.instance,
            )

        if errors:
            raise exceptions.ValidationError(errors)

        return data

    class Meta:
        model: models.Model | None = None
        fields = [
            "created",
            "last_modified",
            "user",
        ]

    class OnyxMeta:
        relations: dict[str, type[BaseRecordSerializer]] = {}
        relation_options: dict[str, dict[str, bool]] = {}
        identifiers: list[str] = []
        optional_value_groups: list[list[str]] = []
        orderings: list[tuple[str, str]] = []
        non_futures: list[str] = []
        choice_constraints: list[tuple[str, str]] = []
        conditional_required: dict[str, list[str]] = {}
        conditional_value_required: dict[tuple[str, Any, Any], list[str]] = {}


class PrimaryRecordSerializer(BaseRecordSerializer):
    """
    Serializer for the 'primary' model of a project.
    """

    site = SiteField(default=CurrentUserSiteDefault())

    class Meta:
        model: models.Model | None = None
        fields = BaseRecordSerializer.Meta.fields + [
            "is_published",
            "published_date",
            "is_suppressed",
            "site",
            "is_site_restricted",
        ]

    class OnyxMeta(BaseRecordSerializer.OnyxMeta):
        anonymised_fields: dict[str, str] = {}


class ProjectRecordSerializer(PrimaryRecordSerializer):
    """
    Serializer for the 'root' model of a project.
    """

    climb_id = serializers.CharField(required=False)

    class Meta:
        model: models.Model | None = None
        fields = PrimaryRecordSerializer.Meta.fields + [
            "climb_id",
        ]

    def to_internal_value(self, data):
        data = super().to_internal_value(data)

        # Retrieve site for use in anonymising fields
        if self.instance:
            site = self.instance.site
        else:
            site = data["site"]

        # Anonymise fields
        # This runs before unique_together checks, but AFTER unique checks
        for field, prefix in self.OnyxMeta.anonymised_fields.items():
            if data.get(field):
                hasher = hashlib.sha256()
                hasher.update(data[field].strip().lower().encode("utf-8"))
                hash = hasher.hexdigest()

                # TODO: This shouldn't really be run in a serializer
                # Anonymiser objects can be unnecessarily created when data is invalid
                anonymiser, _ = Anonymiser.objects.get_or_create(
                    project=self.context["project"],
                    site=site,
                    field=field,
                    hash=hash,
                    defaults={"prefix": prefix},
                )
                data[field] = anonymiser.identifier

        return data


class AnonymiserRelatedField(serializers.SlugRelatedField):
    def get_queryset(self):
        project = self.context["project"]
        queryset = Anonymiser.objects.filter(project=project)
        return queryset


class ProjectRecordsRelatedField(serializers.SlugRelatedField):
    def get_queryset(self):
        model = self.context["project"].content_type.model_class()
        queryset = model.objects.all()
        return queryset


class AnalysisSerializer(PrimaryRecordSerializer):
    """
    Serializer for all project analyses.
    """

    project = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Project.objects.all(), default=CurrentProjectDefault()
    )
    analysis_id = serializers.CharField(required=False)
    experiment_details = StructureField(required=False)
    upstream_analyses = serializers.SlugRelatedField(
        queryset=Analysis.objects.all(),
        many=True,
        required=False,
        slug_field="analysis_id",
    )
    downstream_analyses = serializers.SlugRelatedField(
        queryset=Analysis.objects.all(),
        many=True,
        required=False,
        slug_field="analysis_id",
    )
    identifiers = AnonymiserRelatedField(
        many=True, required=False, slug_field="identifier"
    )

    def __init__(self, *args, fields: dict[str, Any] | None = None, **kwargs):
        super().__init__(*args, fields=fields, **kwargs)

        if fields is not None and "records" in fields:
            self.fields["records"] = ProjectRecordsRelatedField(
                source=f"{self.context['project'].content_type.model_class().__name__.lower()}_records",
                many=True,
                required=False,
                slug_field="climb_id",
            )

    class Meta:
        model = Analysis
        fields = PrimaryRecordSerializer.Meta.fields + [
            "project",
            "analysis_id",
            "analysis_date",
            "name",
            "command_details",
            "pipeline_details",
            "experiment_details",
            "result",
            "report",
            "outputs",
            "upstream_analyses",
            "downstream_analyses",
            "identifiers",
        ]


# TODO: Race condition testing + preventions.
# E.g. could introduce model update_fields argument
# This would mean only changed fields are updated, rather than whole instance
# TODO: Investigate type: ignore statements in SerializerNode
class SerializerNode:
    def __init__(
        self,
        serializer_class: type[BaseRecordSerializer],
        data=None,
        context=None,
    ):
        """
        Initialise a node.
        """

        if not isinstance(data, dict):
            raise exceptions.ValidationError(
                {"non_field_errors": ["Expected a dictionary."]}
            )

        assert serializer_class.Meta.model is not None

        # Assign the serializer class and required properties to the node
        self.serializer_class = serializer_class
        self.model = serializer_class.Meta.model
        self.identifiers = serializer_class.OnyxMeta.identifiers
        self.data = {}
        self.context = context
        self.errors = {}

        # Mapping for accessing linked nodes
        self.nodes = {}

        # Separate the relations from data stored on the node
        relations = serializer_class.OnyxMeta.relations
        relation_options = serializer_class.OnyxMeta.relation_options
        related_data = {}

        for field, field_data in data.items():
            if field in relations:
                related_data[field] = field_data
            else:
                self.data[field] = field_data

        # Check for any missing relations that are required
        required_relations = [
            field
            for field, options in relation_options.items()
            if options.get("required")
        ]
        for field in required_relations:
            if field not in related_data:
                self.errors[field] = ["This field is required."]

        # Initialise related nodes with their data
        for field, field_data in related_data.items():
            serializer = relations[field]
            options = relation_options.get(field, {})

            if options.get("many"):
                if not isinstance(field_data, list):
                    self.errors[field] = ["Expected a list."]
                    continue

                if options.get("required") and len(field_data) < 1:
                    self.errors[field] = ["Expected at least one item."]
                    continue

                for i, f_d in enumerate(field_data):
                    try:
                        node = SerializerNode(
                            serializer_class=serializer,
                            data=f_d,
                            context=context,
                        )
                    except exceptions.ValidationError as e:
                        node = None
                        self.errors.setdefault(field, {})[i] = e.args[0]

                    self.nodes.setdefault(field, []).append(node)
            else:
                try:
                    node = SerializerNode(
                        serializer_class=serializer,
                        data=field_data,
                        context=context,
                    )
                    self.nodes[field] = node
                except exceptions.ValidationError as e:
                    self.errors[field] = e.args[0]

    def _validate_subnode(
        self,
        subnode: SerializerNode,
        link: models.Model | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Prepare/run validation of a subnode.
        """

        if not link:
            # If a link was not provided, the subnode does not exist
            # This is because a subnode cannot already exist without a pre-existing linked instance
            # Therefore, the subnode is validated against the assumption it is being created
            if not subnode.is_valid():
                return False, subnode.errors
        else:
            # If a link was provided, the subnode may exist
            # The subnode's identifiers are mandatory fields that locate an instance, required for either create/update
            # These identifiers are validated, and used to attempt to locate an instance
            # If an instance is found, the subnode validates for update, otherwise it validates for creation
            identifiers = {
                key: value
                for key, value in subnode.data.items()
                if key in subnode.identifiers
            }
            identifier_serializer = subnode.serializer_class(
                data=identifiers,
                partial=True,
            )

            # Determine whether the provided identifiers are valid
            if not identifier_serializer.is_valid():
                return False, identifier_serializer.errors  #  type: ignore

            # Obtain the valid identifiers
            valid_identifiers = identifier_serializer.validated_data
            assert isinstance(valid_identifiers, dict)

            # Use the identifiers to try and locate an instance
            try:
                ins = subnode.model.objects.get(
                    link=link,
                    **valid_identifiers,
                )
            except subnode.model.DoesNotExist:
                ins = None

            # Run validation of the subnode
            # If an instance was found, it is passed into the subnode and this will be validated as an update
            # Otherwise, the subnode is validated for purpose of creating an instance
            if not subnode.is_valid(instance=ins):
                return False, subnode.errors

        return True, {}

    def is_valid(
        self,
        instance: models.Model | None = None,
    ) -> bool:
        """
        Validate a node.
        """

        # Initialise a serializer and validate self.data
        # If an instance was not provided, will validate self.data for creation of an instance
        # If an instance was provided, will validate self.data for partial update of the instance
        self.serializer = self.serializer_class(
            instance=instance,
            data=self.data,
            partial=bool(instance),
            context=self.context,
        )

        valid = [self.serializer.is_valid()]
        self.errors = dict(self.serializer.errors) | self.errors

        # Validate any nested objects, providing a link to the current instance
        for field, node in self.nodes.items():
            if isinstance(node, list):
                # Used to track duplicate identifiers
                identifiers_set = set()

                for i, n in enumerate(node):
                    # Need to check for the existence of the subnode
                    # This is because some may be set to 'None' if they failed __init__ validation
                    # e.g. the subnode may have been provided as a list when expected a dict
                    if n:
                        val, errors = self._validate_subnode(n, link=instance)
                        valid.append(val)

                        if errors:
                            self.errors.setdefault(field, {})[i] = errors
                        else:
                            # We can assume the subnode is otherwise valid
                            # But need to check identifier are unique
                            n_identifiers = tuple(
                                value
                                for key, value in n.serializer.validated_data.items()
                                if key in n.identifiers
                            )
                            if n_identifiers in identifiers_set:
                                if len(n.identifiers) == 1:
                                    self.errors[field] = {
                                        "non_field_errors": [
                                            f"Each {next(iter(n.identifiers))} in this set of {field} must be unique."
                                        ]
                                    }
                                else:
                                    self.errors[field] = {
                                        "non_field_errors": [
                                            f"Each combination of {', '.join(n.identifiers)} in this set of {field} must be unique."
                                        ]
                                    }
                                break
                            identifiers_set.add(n_identifiers)

            else:
                val, errors = self._validate_subnode(node, link=instance)
                valid.append(val)

                if errors:
                    self.errors[field] = errors

        return all(valid) and not self.errors

    def _save(
        self,
        link: models.Model | None = None,
    ) -> models.Model:
        """
        Inner function for saving a node, without being wrapped in a transaction.

        Do NOT call this function outside of the SerializerNode.
        """

        # Save the serializer and retrieve an instance
        # If a link was provided, pass it through to the serializer
        if link:
            instance = self.serializer.save(link=link)
        else:
            instance = self.serializer.save()

        # Save any nested objects, providing a link to the current instance
        for node in self.nodes.values():
            if isinstance(node, list):
                for n in node:
                    if n:
                        n._save(link=instance)
            else:
                node._save(link=instance)

        return instance  #  type: ignore

    def save(self) -> models.Model:
        """
        Save a node.

        Wraps the whole operation in a `transaction.atomic` block, ensuring atomicity of the database.

        This means either all changes to the database triggered by the save are committed, or none of them are.
        """

        try:
            # This context manager ensures that all database operations that
            # occur during the saving of the node are carried out in a single block.
            # If the context manager encounters any DatabaseErrors, it rolls back the transaction.
            with transaction.atomic():
                try:
                    # Attempt to save the node
                    # If successful, returns the saved instance
                    instance = self._save()
                except Exception as e:
                    # Catch all exceptions thrown during the saving process, and re-raise them as DatabaseErrors.
                    # This means ANY error will cause the entire database transaction to be rolled back.
                    raise DatabaseError from e

        except DatabaseError as e:
            # TODO: The below behaviour was changed after I noticed a particularly exposing IntegrityError.
            # Will just have to see if a lack of information regarding these proves to be a problem for users or not.
            assert e.__cause__ is not None
            raise e.__cause__

        return instance
