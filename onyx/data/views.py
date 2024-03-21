from __future__ import annotations
import hashlib
from collections import namedtuple
from pydantic import RootModel, ValidationError as PydanticValidationError
from django.db.models import Count
from rest_framework import status, exceptions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.pagination import CursorPagination
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSetMixin
from utils.functions import parse_permission
from accounts.permissions import Approved, ProjectApproved, IsSiteMember
from .models import Project, Choice, ProjectRecord, Anonymiser
from .serializers import SerializerNode, SummarySerializer, IdentifierSerializer
from .exceptions import ClimbIDNotFound, IdentifierNotFound
from .query import make_atoms, validate_atoms, make_query
from .queryset import init_project_queryset, prefetch_nested
from .types import OnyxType
from .actions import Actions
from .spec import generate_fields_spec
from .fields import (
    FieldHandler,
    flatten_fields,
    unflatten_fields,
    include_exclude_fields,
)


class RequestBody(RootModel):
    """
    Generic structure for the body of a request.

    This is used to validate the body of POST and PATCH requests.
    """

    root: dict[str, RequestBody | list[RequestBody] | str | int | float | bool | None]


class ProjectAPIView(APIView):
    """
    `APIView` with some additional initial setup for working with a specific project.
    """

    def initial(self, request: Request, *args, **kwargs):
        """
        Initial setup for working with project data.
        """

        super().initial(request, *args, **kwargs)

        # Get the project
        self.project = Project.objects.get(code__iexact=kwargs["code"])

        # Get the project's model
        model = self.project.content_type.model_class()
        assert model is not None
        assert issubclass(model, ProjectRecord)
        self.model = model

        # Get the model's serializer
        self.serializer_cls = self.kwargs["serializer_class"]
        self.kwargs.pop("serializer_class")

        # Initialise field handler for the project, action and user
        self.handler = FieldHandler(
            project=self.project,
            action=self.project_action,  # type: ignore
            user=request.user,
        )

        # Build request query parameters
        self.query_params = [
            {field: value}
            for field in request.query_params
            for value in request.query_params.getlist(field)
            if field not in {"cursor", "include", "exclude", "summarise"}
        ]

        # Build extra query parameters
        # Cursor pagination
        self.cursor = request.query_params.get("cursor")

        # Include fields in output of get/filter/query
        self.include = list(request.query_params.getlist("include"))

        # Excluding fields in output of get/filter/query
        self.exclude = list(request.query_params.getlist("exclude"))

        # Summary aggregate in filter/query
        self.summarise = list(request.query_params.getlist("summarise"))

        # Build request body
        try:
            self.request_data = RequestBody.model_validate(request.data).model_dump(
                mode="python"
            )
        except PydanticValidationError as e:
            # Transform pydantic validation errors into DRF-style validation errors
            errors = {}

            for error in e.errors(
                include_url=False, include_context=False, include_input=False
            ):
                if not error["loc"]:
                    errors.setdefault("non_field_errors", []).append(error["msg"])
                else:
                    errors.setdefault(error["loc"][0], []).append(error["msg"])

            for name, errs in errors.items():
                errors[name] = list(set(errs))

            raise exceptions.ValidationError(errors)


class ProjectsView(APIView):
    permission_classes = Approved

    def get(self, request: Request) -> Response:
        """
        List all projects that the user has allowed actions on.
        """

        # Filter user groups to determine all (project, scope, actions) tuples
        project_groups = []
        for project, scope, actions_str in (
            request.user.groups.filter(projectgroup__isnull=False)
            .values_list(
                "projectgroup__project__code",
                "projectgroup__scope",
                "projectgroup__actions",
            )
            .distinct()
        ):
            project_groups.append(
                {
                    "project": project,
                    "scope": scope,
                    "actions": [
                        action.value
                        for action in Actions
                        if action.value in actions_str
                    ],
                }
            )

        # Return list of allowed project groups
        return Response(project_groups)


class FieldsView(ProjectAPIView):
    permission_classes = ProjectApproved
    project_action = "access"

    def get(self, request: Request, code: str) -> Response:
        """
        List all fields for a given project.
        """

        # Get all accessible fields
        fields = self.handler.get_fields()

        # Get all actions for each field (excluding access)
        actions_map = {}
        for permission in request.user.get_all_permissions():
            _, action, project, field = parse_permission(permission)

            if action != "access" and project == self.project.code and field in fields:
                actions_map.setdefault(field, []).append(action)

        # Determine OnyxField objects for each field
        onyx_fields = self.handler.resolve_fields(fields)

        # Generate fields specification
        fields_spec = generate_fields_spec(
            unflatten_fields(fields),
            onyx_fields=onyx_fields,
            actions_map=actions_map,
            serializer=self.serializer_cls,
        )

        # Return response with project information and fields
        return Response(
            {
                "name": self.project.name,
                "description": self.project.description,
                "version": self.model.version(),
                "fields": fields_spec,
            }
        )


class LookupsView(ProjectAPIView):
    permission_classes = ProjectApproved
    project_action = "access"

    def get(self, request: Request, code: str) -> Response:
        """
        List all lookups.
        """

        # Build lookups structure with allowed lookups for each type
        lookups = {onyx_type.label: onyx_type.lookups for onyx_type in OnyxType}

        # Return the types and their lookups
        return Response(lookups)


class ChoicesView(ProjectAPIView):
    permission_classes = ProjectApproved
    project_action = "access"

    def get(self, request: Request, code: str, field: str) -> Response:
        """
        List all choices for a given field.
        """

        # Determine OnyxField object for the field
        try:
            onyx_field = self.handler.resolve_field(field)
        except exceptions.ValidationError as e:
            raise exceptions.ValidationError({"detail": e.args[0]})

        if onyx_field.onyx_type != OnyxType.CHOICE:
            raise exceptions.ValidationError(
                {"detail": f"This field is not a {OnyxType.CHOICE.label} field."}
            )

        # Obtain choices for the field
        choices = Choice.objects.filter(
            project_id=self.project.code,
            field=onyx_field.field_name,
            is_active=True,
        ).values_list(
            "choice",
            flat=True,
        )

        # Return choices for the field
        return Response(sorted(choices))


class IdentifyView(ProjectAPIView):
    permission_classes = ProjectApproved + [IsSiteMember]
    project_action = "identify"

    def post(self, request: Request, code: str, field: str) -> Response:
        """
        Retrieve the identifier for a given `value` of the given `field`.
        """

        # Validate the request field
        try:
            self.handler.resolve_field(field)
        except exceptions.ValidationError as e:
            raise exceptions.ValidationError({"detail": e.args[0]})

        # Validate request body
        serializer = IdentifierSerializer(
            data=self.request_data,
            context={
                "project": self.project,
                "request": self.request,
            },
        )
        if not serializer.is_valid():
            raise exceptions.ValidationError(serializer.errors)

        # Check permissions to identify the instance
        site = serializer.validated_data["site"]  #  type: ignore
        SiteObject = namedtuple("SiteObject", ["site"])
        site_obj = SiteObject(site=site)
        self.check_object_permissions(request, site_obj)

        # Hash the value
        value = serializer.validated_data["value"]  #  type: ignore
        hasher = hashlib.sha256()
        hasher.update(value.strip().lower().encode("utf-8"))
        hash = hasher.hexdigest()

        # Get the anonymised field data from the hash
        try:
            anonymised_field = Anonymiser.objects.get(
                project=self.project,
                site=site,
                field=field,
                hash=hash,
            )
        except Anonymiser.DoesNotExist:
            raise IdentifierNotFound

        # Return information regarding the identifier
        return Response(
            {
                "project": self.project.code,
                "site": anonymised_field.site.code,
                "field": field,
                "value": value,
                "identifier": anonymised_field.identifier,
            }
        )


class ProjectRecordsViewSet(ViewSetMixin, ProjectAPIView):
    permission_classes = ProjectApproved + [IsSiteMember]

    def initial(self, request: Request, *args, **kwargs):
        match (self.request.method, self.action):
            case ("POST", "create"):
                self.project_action = "add"

            case ("POST", "list"):
                self.project_action = "list"

            case ("GET", "retrieve") | ("HEAD", "retrieve"):
                self.project_action = "get"

            case ("GET", "list") | ("HEAD", "list"):
                self.project_action = "list"

            case ("PATCH", "partial_update"):
                self.project_action = "change"

            case ("DELETE", "destroy"):
                self.project_action = "delete"

            case ("OPTIONS", "metadata"):
                self.project_action = "access"

            case _:
                raise exceptions.MethodNotAllowed(self.request.method)

        super().initial(request, *args, **kwargs)

    def create(self, request: Request, code: str, test: bool = False) -> Response:
        """
        Create an instance for the given project `code`.
        """

        # Validate the request data fields
        self.handler.resolve_fields(flatten_fields(self.request_data))

        # Validate the data
        node = SerializerNode(
            self.serializer_cls,
            data=self.request_data,
            context={
                "project": self.project,
                "request": self.request,
            },
        )

        if not node.is_valid():
            raise exceptions.ValidationError(node.errors)

        if not test:
            # Create the instance
            instance = node.save()

            # Set of fields to return in response
            # This includes the climb_id and any anonymised fields
            identifier_fields = ["climb_id"] + list(
                self.serializer_cls.OnyxMeta.anonymised_fields.keys()
            )

            # Serialize the result
            serializer = self.serializer_cls(
                instance,
                fields=unflatten_fields(identifier_fields),
            )
            data = serializer.data
        else:
            data = {}

        # Return response indicating creation
        return Response(data, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, code: str, climb_id: str) -> Response:
        """
        Use the `climb_id` to retrieve an instance for the given project `code`.
        """

        # Validate the include/exclude fields
        self.handler.resolve_fields(self.include + self.exclude)

        # Initial queryset
        qs = init_project_queryset(
            model=self.model,
            user=request.user,
            fields=self.handler.get_fields(),
        )

        # Get the instance
        # If the instance does not exist, return 404
        try:
            instance = qs.get(climb_id=climb_id)
        except self.model.DoesNotExist:
            raise ClimbIDNotFound

        # Fields returned in response
        fields = include_exclude_fields(
            fields=self.handler.get_fields(),
            include=self.include,
            exclude=self.exclude,
        )

        # Serialize the result
        serializer = self.serializer_cls(
            instance,
            fields=unflatten_fields(fields),
        )

        # Return response with data
        return Response(serializer.data)

    def list(self, request: Request, code: str) -> Response:
        """
        Filter and list instances for the given project `code`.
        """

        # If method == GET, then parameters were provided in the query_params
        # Convert these into the same format as the JSON provided when method == POST
        if request.method == "GET":
            query = self.query_params
            if query:
                query = {"&": query}
        else:
            query = self.request_data

        # If a query was provided
        # Turn the value of each key-value pair in query into a 'QueryAtom' object
        # A list of QueryAtoms is returned
        if query:
            atoms = make_atoms(query)  # type: ignore
        else:
            atoms = []

        # Validate fields
        field_errors = {}
        filter_fields = {}
        summary_fields = {}
        filter_handler = FieldHandler(
            project=self.project,
            action="filter",
            user=request.user,
        )

        # Validate filter fields and determine OnyxField objects
        # If a summary is being carried out on one or more fields
        # then any field involved in filtering will also be included
        for atom in atoms:
            try:
                # Lookups are allowed for filter fields
                resolved_field = filter_handler.resolve_field(
                    atom.key, allow_lookup=True
                )

                # The key used in filter_fields includes the field_path + lookup
                filter_fields[atom.key] = resolved_field

                # The key used in summary_fields is just the field_path
                summary_fields[resolved_field.field_path] = resolved_field

            except exceptions.ValidationError as e:
                field_errors.setdefault(atom.key, []).append(e.args[0])

        # Validate summarise fields and determine OnyxField objects
        if self.summarise:
            for field in self.summarise:
                try:
                    # Lookups are not allowed for summarise fields
                    summary_fields[field] = filter_handler.resolve_field(field)

                except exceptions.ValidationError as e:
                    field_errors.setdefault(field, []).append(e.args[0])

            # Reject any relational fields in a summary
            for field, onyx_field in summary_fields.items():
                if onyx_field.onyx_type == OnyxType.RELATION:
                    field_errors.setdefault(field, []).append(
                        "Cannot summarise over a relational field."
                    )

        # Validate include/exclude fields
        include_exclude = self.include + self.exclude
        for field in include_exclude:
            try:
                # Lookups are not allowed for include/exclude fields
                self.handler.resolve_field(field)

            except exceptions.ValidationError as e:
                field_errors.setdefault(field, []).append(e.args[0])

        if field_errors:
            raise exceptions.ValidationError(field_errors)

        # Validate and clean the provided key-value pairs
        # This is done by first building a FilterSet
        # And then checking the underlying form is valid
        validate_atoms(self.model, atoms, filter_fields)

        # Initial queryset
        qs = init_project_queryset(
            model=self.model,
            user=request.user,
            fields=self.handler.get_fields(),
        )

        # Fields returned in response
        fields = include_exclude_fields(
            fields=self.handler.get_fields(),
            include=self.include,
            exclude=self.exclude,
        )

        # Prefetch nested fields returned in response
        qs = prefetch_nested(qs, unflatten_fields(fields))

        # If data was provided, then it has now been validated
        # So we form the Q object, and filter the queryset with it
        if query:
            q_object = make_query(query)  # type: ignore

            # A queryset is not guaranteed to return unique objects
            # Especially as a result of complex nested queries
            # So a call to distinct is necessary.
            # This (should) not affect the cursor pagination
            # as removing duplicates is not changing any order in the result set
            # TODO: Tests will be needed to confirm all of this
            qs = qs.filter(q_object).distinct()

        if self.summarise:
            summary_values = qs.values(*summary_fields.keys())

            # Reject summary if it would return too many distinct values
            if summary_values.distinct().count() > 100000:
                raise exceptions.ValidationError(
                    {
                        "detail": "The current summary would return too many distinct values."
                    }
                )

            # Serialize the results
            serializer = SummarySerializer(
                summary_values.annotate(count=Count("*")).order_by(
                    *summary_fields.keys()
                ),
                serializer_cls=self.serializer_cls,
                onyx_fields=summary_fields,
                many=True,
            )
        else:
            # Prepare paginator
            self.paginator = CursorPagination()
            self.paginator.ordering = "created"

            # Paginate the response
            result_page = self.paginator.paginate_queryset(qs, request)

            # Serialize the results
            serializer = self.serializer_cls(
                result_page,
                many=True,
                fields=unflatten_fields(fields),
            )

        # Return response with either filtered set of data, or summarised values
        return Response(serializer.data)

    def partial_update(
        self, request: Request, code: str, climb_id: str, test: bool = False
    ) -> Response:
        """
        Use the `climb_id` to update an instance for the given project `code`.
        """

        # Validate the request data fields
        self.handler.resolve_fields(flatten_fields(self.request_data))

        # Initial queryset
        qs = init_project_queryset(
            model=self.model,
            user=request.user,
            fields=self.handler.get_fields(),
        )

        # Get the instance to be updated
        # If the instance does not exist, return 404
        try:
            instance = qs.get(climb_id=climb_id)
        except self.model.DoesNotExist:
            raise ClimbIDNotFound

        # Check permissions to update the instance
        self.check_object_permissions(request, instance)

        # Validate the data
        node = SerializerNode(
            self.serializer_cls,
            data=self.request_data,
            context={
                "project": self.project,
                "request": self.request,
            },
        )

        if not node.is_valid(instance=instance):
            raise exceptions.ValidationError(node.errors)

        if not test:
            # Update the instance
            instance = node.save()

            # Set of fields to return in response
            # This includes the climb_id and any anonymised fields
            identifier_fields = ["climb_id"] + list(
                self.serializer_cls.OnyxMeta.anonymised_fields.keys()
            )

            # Serialize the result
            serializer = self.serializer_cls(
                instance,
                fields=unflatten_fields(identifier_fields),
            )
            data = serializer.data
        else:
            data = {}

        # Return response indicating update
        return Response(data)

    def destroy(self, request: Request, code: str, climb_id: str) -> Response:
        """
        Use the `climb_id` to permanently delete an instance of the given project `code`.
        """

        # Initial queryset
        qs = init_project_queryset(
            model=self.model,
            user=request.user,
            fields=self.handler.get_fields(),
        )

        # Get the instance to be deleted
        # If the instance does not exist, return 404
        try:
            instance = qs.get(climb_id=climb_id)
        except self.model.DoesNotExist:
            raise ClimbIDNotFound

        # Check permissions to delete the instance
        self.check_object_permissions(request, instance)

        # Delete the instance
        instance.delete()

        # Set of fields to return in response
        # This includes the climb_id and any anonymised fields
        identifier_fields = ["climb_id"] + list(
            self.serializer_cls.OnyxMeta.anonymised_fields.keys()
        )

        # Serialize the result
        serializer = self.serializer_cls(
            instance,
            fields=unflatten_fields(identifier_fields),
        )
        data = serializer.data

        # Return response indicating deletion
        return Response(data)
