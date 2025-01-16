from __future__ import annotations
import hashlib
import pydantic.validators
from typing_extensions import Annotated
from collections import namedtuple
import pydantic
from django.conf import settings
from django.db.models import Count, Subquery, Q
from rest_framework import status, exceptions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSetMixin
from utils.functions import parse_permission, pydantic_to_drf_error
from accounts.permissions import Approved, ProjectApproved, IsSiteMember
from accounts.models import Site
from .models import Project, Choice, ProjectRecord, Anonymiser, Analysis
from .serializers import (
    HistoryDiffSerializer,
    SummarySerializer,
    IdentifierSerializer,
    SerializerNode,
    AnalysisSerializer,
)
from .exceptions import ClimbIDNotFound, IdentifierNotFound, AnalysisIdNotFound
from .query import QuerySymbol, QueryBuilder
from .search import build_search
from .queryset import init_project_queryset, prefetch_nested
from .types import OnyxType, OnyxLookup
from .actions import Actions
from .spec import generate_fields_spec
from .fields import (
    FieldHandler,
    flatten_fields,
    unflatten_fields,
    include_exclude_fields,
)


def get_discriminator_value(obj):
    if type(obj) == dict:
        return "dict"

    elif type(obj) == list:
        return "list"

    elif type(obj) == str:
        return "str"

    elif type(obj) == int:
        return "int"

    elif type(obj) == float:
        return "float"

    elif type(obj) == bool:
        return "bool"

    elif obj is None:
        return "null"

    else:
        return None


class RequestBody(pydantic.RootModel):
    """
    Generic structure for the body of a request.

    This is used to validate the body of POST and PATCH requests.
    """

    root: dict[
        str,
        Annotated[
            Annotated[RequestBody, pydantic.Tag("dict")]
            | Annotated[
                list[RequestBody | str | int | float | bool | None],
                pydantic.Tag("list"),
                pydantic.Field(max_length=settings.ONYX_CONFIG["MAX_ITERABLE_INPUT"]),
            ]
            | Annotated[str, pydantic.Tag("str")]
            | Annotated[int, pydantic.Tag("int")]
            | Annotated[float, pydantic.Tag("float")]
            | Annotated[bool, pydantic.Tag("bool")]
            | Annotated[None, pydantic.Tag("null")],
            pydantic.Discriminator(get_discriminator_value),
        ],
    ] = pydantic.Field(max_length=settings.ONYX_CONFIG["MAX_ITERABLE_INPUT"])


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
            action=self.project_action.label,  # type: ignore
            user=request.user,
        )

        # Build request query parameters
        self.query_params = [
            {field: value}
            for field in request.query_params
            for value in request.query_params.getlist(field)
            if field
            not in {
                "cursor",
                "include",
                "exclude",
                "summarise",
                "search",
                "page",
                "order",
            }
        ]

        # Build extra query parameters
        # Cursor for pagination
        self.cursor = request.query_params.get("cursor")

        # Page number for pagination
        self.page = request.query_params.get("page")

        # Include fields in output of get/filter/query
        self.include = list(request.query_params.getlist("include"))

        # Excluding fields in output of get/filter/query
        self.exclude = list(request.query_params.getlist("exclude"))

        # Order of fields in filter/query
        self.order = request.query_params.get("order")

        # Summary aggregate in filter/query
        self.summarise = list(request.query_params.getlist("summarise"))

        # Search used in filter/query
        self.search = request.query_params.get("search")

        # Build request body
        try:
            request_data = RequestBody.model_validate(request.data).model_dump(
                mode="python"
            )
            assert isinstance(request_data, dict)
            self.request_data = request_data
        except pydantic.ValidationError as e:
            raise pydantic_to_drf_error(e)


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
                        action.label
                        for action in Actions
                        if action != Actions.ACCESS and action.label in actions_str
                    ],
                }
            )

        # Return list of allowed project groups
        return Response(project_groups)


class TypesView(APIView):
    permission_classes = Approved

    def get(self, request: Request) -> Response:
        """
        List available types.
        """

        # Build types structure with allowed lookups for each type
        types = [
            {
                "type": onyx_type.label,
                "description": onyx_type.description,
                "lookups": [lookup for lookup in onyx_type.lookups if lookup],
            }
            for onyx_type in OnyxType
        ]

        # Return the types and their lookups
        return Response(types)


class LookupsView(APIView):
    permission_classes = Approved

    def get(self, request: Request) -> Response:
        """
        List available lookups.
        """

        # Build lookups structure with allowed types for each lookup
        lookups = [
            {
                "lookup": onyx_lookup.label,
                "description": onyx_lookup.description,
                "types": [
                    onyx_type.label
                    for onyx_type in OnyxType
                    if onyx_lookup.label in onyx_type.lookups
                ],
            }
            for onyx_lookup in OnyxLookup
        ]

        # Return the types and their lookups
        return Response(lookups)


class FieldsView(ProjectAPIView):
    permission_classes = ProjectApproved
    project_action = Actions.ACCESS

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

            if (
                action != Actions.ACCESS.label
                and project == self.project.code
                and field in fields
            ):
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


class ChoicesView(ProjectAPIView):
    permission_classes = ProjectApproved
    project_action = Actions.ACCESS

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
        choices = {
            choice: {"description": description, "is_active": is_active}
            for choice, description, is_active in Choice.objects.filter(
                project=self.project,
                field=onyx_field.field_name,
            )
            .order_by("choice")
            .values_list(
                "choice",
                "description",
                "is_active",
            )
        }

        # Populate site choice descriptions from the Site model description
        if onyx_field.field_name == "site":
            descriptions = {
                site_code: description
                for site_code, description in Site.objects.values_list(
                    "code", "description"
                )
            }

            for choice, data in choices.items():
                if not data["description"]:
                    data["description"] = descriptions.get(choice.lower(), "")

        # Return choices for the field
        return Response(choices)


class HistoryView(ProjectAPIView):
    permission_classes = ProjectApproved + [IsSiteMember]
    project_action = Actions.HISTORY

    def get(self, request: Request, code: str, climb_id: str) -> Response:
        """
        Use the `climb_id` to retrieve the history of an instance for the given project `code`.
        """

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

        # Check permissions to view the history of the instance
        try:
            # If the user is a site member or staff, then they can view value changes
            self.check_object_permissions(request, instance)
            show_values = True
        except exceptions.PermissionDenied:
            # Otherwise, only the history of the instance can be viewed
            show_values = False

        # Get instances corresponding to the history of the instance
        history = list(instance.history.all().order_by("history_date"))  #  type: ignore

        # Mapping of all history fields to their corresponding OnyxField objects
        fields = self.handler.resolve_fields(self.handler.get_fields())

        # Non-nested fields to include in the history
        included_fields = [
            field for field in self.serializer_cls.Meta.fields if field in fields
        ]

        # Nested fields to include in the history
        # These fields are mapped to their corresponding history model
        included_nested_fields = {
            nested_field: nested_serializer.Meta.model.history.model
            for nested_field, nested_serializer in self.serializer_cls.OnyxMeta.relations.items()
            if nested_field in fields
        }

        # Mapping of history types to Onyx action labels
        actions = {
            "+": Actions.ADD.label,
            "~": Actions.CHANGE.label,
            "-": Actions.DELETE.label,
        }

        # Iterate through the instance's history, building a list of differences over time
        diffs = []
        HIDDEN = "XXXX"
        for i, h in enumerate(history):
            diff = {
                "username": h.history_user.username if h.history_user else None,
                "timestamp": h.history_date,
                "action": actions[h.history_type],
                "changes": [],
            }

            # If the history type is a change, then include the changes
            if h.history_type == "~":
                # Create a list of all direct changes to the instance
                # These changes need to be serialized so the output field
                # values are represented correctly (e.g. the correct date format)
                diff["changes"].extend(
                    HistoryDiffSerializer(
                        {
                            "field": change.field,
                            "type": fields[change.field].onyx_type.label,
                            "from": change.old if show_values else HIDDEN,
                            "to": change.new if show_values else HIDDEN,
                        },
                        serializer_cls=self.serializer_cls,
                        onyx_field=fields[change.field],
                        show_values=show_values,
                    ).data
                    for change in h.diff_against(
                        history[i - 1],
                        included_fields=included_fields,
                    ).changes
                )

                # Date of the next history entry by the same user
                next_user_history_date = None
                for next_h in history[i + 1 :]:
                    if next_h.history_user == h.history_user:
                        next_user_history_date = next_h.history_date
                        break

                # For each nested field, append counts of changes
                for (
                    nested_field,
                    nested_history_model,
                ) in included_nested_fields.items():
                    if next_user_history_date is None:
                        # If this is the latest change the user made,
                        # then include all user changes up to the present
                        nested_diffs = (
                            nested_history_model.objects.filter(
                                link__climb_id=climb_id,
                                history_user=h.history_user,
                                history_date__gte=h.history_date,
                            )
                            .values("history_type")
                            .annotate(count=Count("history_type"))
                        )
                    else:
                        # Otherwise, include all changes up to the user's next history entry
                        nested_diffs = (
                            nested_history_model.objects.filter(
                                link__climb_id=climb_id,
                                history_user=h.history_user,
                                history_date__gte=h.history_date,
                                history_date__lt=next_user_history_date,
                            )
                            .values("history_type")
                            .annotate(count=Count("history_type"))
                        )

                    for nested_diff in nested_diffs:
                        diff["changes"].append(
                            {
                                "field": nested_field,
                                "type": fields[nested_field].onyx_type.label,
                                "action": actions[nested_diff["history_type"]],
                                "count": nested_diff["count"],
                            }
                        )

            diffs.append(diff)

        # Return history
        return Response(
            {
                "climb_id": climb_id,
                "history": diffs,
            }
        )


class IdentifyView(ProjectAPIView):
    permission_classes = ProjectApproved + [IsSiteMember]
    project_action = Actions.IDENTIFY

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


class ProjectViewSet(ViewSetMixin, ProjectAPIView):
    """
    `ViewSet` with some additional initial setup for working with a specific project.
    """

    def initial(self, request: Request, *args, **kwargs):
        match (self.request.method, self.action):
            case ("POST", "create"):
                self.project_action = Actions.ADD

            case ("POST", "list"):
                self.project_action = Actions.LIST

            case ("GET", "retrieve") | ("HEAD", "retrieve"):
                self.project_action = Actions.GET

            case ("GET", "list") | ("HEAD", "list"):
                self.project_action = Actions.LIST

            case ("PATCH", "partial_update"):
                self.project_action = Actions.CHANGE

            case ("DELETE", "destroy"):
                self.project_action = Actions.DELETE

            case ("OPTIONS", "metadata"):
                self.project_action = Actions.ACCESS

            case _:
                raise exceptions.MethodNotAllowed(self.request.method)

        super().initial(request, *args, **kwargs)


class ProjectRecordsViewSet(ProjectViewSet):
    permission_classes = ProjectApproved + [IsSiteMember]

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

    def list(self, request: Request, code: str, count: bool = False) -> Response:
        """
        Filter and list instances for the given project `code`.
        """

        # If method == GET, then parameters were provided in the query_params
        # Convert these into the same format as the JSON provided when method == POST
        if request.method == "GET":
            data = (
                {QuerySymbol.AND.value: self.query_params} if self.query_params else {}
            )
        else:
            data = self.request_data

        errors = {}
        filter_handler = FieldHandler(
            project=self.project,
            action=Actions.FILTER.label,
            user=request.user,
        )

        # Validate include/exclude fields
        for field in self.include + self.exclude:
            try:
                # Lookups are not allowed for include/exclude fields
                self.handler.resolve_field(field)
            except exceptions.ValidationError as e:
                errors.setdefault(field, []).append(e.args[0])

        # Validate order field
        if self.order:
            try:
                # Lookups are not allowed for the order field
                self.handler.resolve_field(self.order.removeprefix("-"))
            except exceptions.ValidationError as e:
                errors.setdefault(self.order, []).append(e.args[0])

        # Validate the query fields
        if data:
            query = QueryBuilder(data, filter_handler)
            if not query.is_valid():
                for filter_name, errs in query.errors.items():
                    errors.setdefault(filter_name, []).extend(errs)
        else:
            query = None

        # Validate summarise fields
        summary_fields = {}
        if self.summarise:
            for field in self.summarise:
                try:
                    # Lookups are not allowed for summarise fields
                    summary_fields[field] = filter_handler.resolve_field(field)
                except exceptions.ValidationError as e:
                    errors.setdefault(field, []).append(e.args[0])

            if query:
                # Add query fields to the summarise fields
                for onyx_field in query.onyx_fields:
                    if onyx_field.field_path not in summary_fields:
                        summary_fields[onyx_field.field_path] = onyx_field

            # Reject any relational fields
            for field, onyx_field in summary_fields.items():
                if onyx_field.onyx_type == OnyxType.RELATION:
                    errors.setdefault(field, []).append(
                        "Cannot summarise over a relational field."
                    )

        if errors:
            raise exceptions.ValidationError(errors)

        # Initial queryset
        init_qs = init_project_queryset(
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
        qs = prefetch_nested(init_qs, unflatten_fields(fields))

        # Q object for the user's search and query
        q_object = Q()

        # If the search parameter was provided
        # Form the Q object for it, and add it to the user's Q object
        if self.search:
            # Get the fields to search over
            search_fields = [
                field
                for field, onyx_field in self.handler.resolve_fields(fields).items()
                if onyx_field.onyx_type == OnyxType.TEXT
                or onyx_field.onyx_type == OnyxType.CHOICE
            ]

            # Form the Q object for the search, and add it to the user's Q object
            q_object &= build_search(self.search, search_fields)

        # If a valid query was provided
        # Form the Q object for it, and add it to the user's Q object
        if query:
            q_object &= query.build()

        if self.summarise:
            # Filter the queryset with the user's Q object
            if q_object:
                qs = qs.filter(q_object)

            relations = {
                onyx_field.field_model: summary_field
                for summary_field, onyx_field in summary_fields.items()
                if onyx_field.field_model != self.model
            }

            if relations:
                # Summarising over more than one related table is disallowed.
                # The resulting counts grow large very quickly.
                if len(relations) > 1:
                    raise exceptions.ValidationError(
                        {"detail": "Cannot summarise over more than one related table."}
                    )

                # Get the relation name
                relation = "__".join(next(iter(relations.values())).split("__")[:-1])

                # When doing a summary involving a related table, we first exclude records that have no relations on that table.
                # This is because otherwise, the counts involving None values for related fields can mean multiple things.
                # The count would either be the number of related rows that have no value for the related field,
                # or the number of rows in the main table that have no related rows.
                qs = qs.filter(
                    id__in=Subquery(
                        init_qs.filter(**{f"{relation}__isnull": False}).values("id")
                    )
                )
                count_name = f"{relation}__count"
            else:
                count_name = "count"

            # Get the summary values
            summary_values = qs.values(*summary_fields.keys())

            # Reject summary if it would return too many distinct values
            if (
                summary_values.distinct().count()
                > settings.ONYX_CONFIG["MAX_SUMMARY_OUTPUT"]
            ):
                raise exceptions.ValidationError(
                    {
                        "detail": "The current summary would return too many distinct values."
                    }
                )

            # Annotate the summary values with the count
            summary = summary_values.annotate(**{count_name: Count("*")}).order_by(
                *summary_fields.keys()
            )

            # Serialize the results
            serializer = SummarySerializer(
                summary,
                serializer_cls=self.serializer_cls,
                onyx_fields=summary_fields,
                count_name=count_name,
                many=True,
            )
        else:
            # Filter the queryset with the user's Q object
            if q_object:
                qs = qs.filter(id__in=Subquery(qs.filter(q_object).values("id")))

            # If the count option is True, return the queryset count instead of results
            if count:
                return Response({"count": qs.count()})

            # Prepare paginator
            if self.order or self.page:
                self.paginator = PageNumberPagination()

                if self.order:
                    reverse = self.order.startswith("-")

                    qs = qs.order_by(self.order, f"{'-' if reverse else ''}created")
                else:
                    qs = qs.order_by("created")
            else:
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


class RecordAnalysesView(ProjectAPIView):
    permission_classes = ProjectApproved + [IsSiteMember]
    project_action = Actions.LIST

    def get(self, request: Request, code: str, climb_id: str) -> Response:
        """
        Use the `climb_id` to retrieve the analyses of an instance for the given project `code`.
        """

        # Initial queryset
        qs = init_project_queryset(
            model=self.model,
            user=request.user,
            fields=self.handler.get_fields(),
        )

        # Check the instance exists
        # If the instance does not exist, return 404
        if not qs.filter(climb_id=climb_id).exists():
            raise ClimbIDNotFound

        # Filter the analyses with the instance's climb_id
        qs = Analysis.objects.filter(
            **{
                "project": self.project,
                f"{ self.model.__name__.lower()}_records__climb_id": climb_id,
            }
        )

        # Serialize the results
        serializer = AnalysisSerializer(
            qs,
            many=True,
            context={"project": self.project, "model": self.model},
        )

        # Return response with data
        return Response(serializer.data)


class AnalysisViewSet(ProjectViewSet):
    permission_classes = ProjectApproved + [IsSiteMember]

    def create(self, request: Request, code: str) -> Response:
        """
        Create an analysis for the given project `code`.
        """

        # Validate the data
        serializer = AnalysisSerializer(
            data=self.request_data,
            context={
                "project": self.project,
                "request": self.request,
                "model": self.model,
            },
        )

        if not serializer.is_valid():
            raise exceptions.ValidationError(serializer.errors)

        # Create the instance
        instance = serializer.save()
        assert isinstance(instance, Analysis)

        # Return response indicating creation
        return Response(
            {"analysis_id": instance.analysis_id}, status=status.HTTP_201_CREATED
        )

    def retrieve(self, request: Request, code: str, analysis_id: int) -> Response:
        """
        Use the `analysis_id` to retrieve an analysis for the given project `code`.
        """

        fields = [
            "analysis_id",
            "published_date",
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
            "records",
        ]

        # Initial queryset
        qs = init_project_queryset(
            model=Analysis,
            user=request.user,
            fields=fields,
        )

        # Get the instance
        # If the instance does not exist, return 404
        try:
            instance = qs.get(project=self.project, analysis_id=analysis_id)
        except Analysis.DoesNotExist:
            raise AnalysisIdNotFound

        # Serialize the result
        serializer = AnalysisSerializer(
            instance,
            context={"project": self.project, "model": self.model},
            fields=unflatten_fields(fields),
        )

        # Return response with data
        return Response(serializer.data)

    def list(self, request: Request, code: str, count: bool = False) -> Response:
        """
        Filter and list analyses for the given project `code`.
        """

        fields = [
            "analysis_id",
            "analysis_date",
            "published_date",
            "name",
            "result",
            "report",
            "outputs",
        ]

        # Initial queryset
        qs = init_project_queryset(
            model=Analysis,
            user=request.user,
            fields=self.handler.get_fields(),
        ).filter(project=self.project)

        # Fields returned in response
        fields = include_exclude_fields(
            fields=fields,
            include=self.include,
            exclude=self.exclude,
        )

        # If the search parameter was provided
        # Filter the queryset with the user's search
        if self.search:
            qs = qs.filter(build_search(self.search, fields))

        # If the count option is True, return the queryset count instead of results
        if count:
            return Response({"count": qs.count()})

        # Prepare paginator
        if self.order or self.page:
            self.paginator = PageNumberPagination()

            if self.order:
                reverse = self.order.startswith("-")

                qs = qs.order_by(self.order, f"{'-' if reverse else ''}created")
            else:
                qs = qs.order_by("created")
        else:
            self.paginator = CursorPagination()
            self.paginator.ordering = "created"

        # Paginate the response
        result_page = self.paginator.paginate_queryset(qs, request)

        # Serialize the results
        serializer = AnalysisSerializer(
            result_page,
            many=True,
            context={"project": self.project, "model": self.model},
            fields=unflatten_fields(fields),
        )

        # Return response with data
        return Response(serializer.data)

    def partial_update(self, request: Request, code: str, analysis_id: int) -> Response:
        """
        Use the `analysis_id` to update an analysis for the given project `code`.
        """

        # Get the instance to be updated
        # If the instance does not exist, return 404
        try:
            instance = Analysis.objects.get(
                project=self.project, analysis_id=analysis_id
            )
        except Analysis.DoesNotExist:
            raise AnalysisIdNotFound

        # Validate the data
        serializer = AnalysisSerializer(
            instance,
            data=self.request_data,
            context={"project": self.project, "model": self.model},
            partial=True,
        )

        if not serializer.is_valid():
            raise exceptions.ValidationError(serializer.errors)

        # Update the instance
        instance = serializer.save()
        assert isinstance(instance, Analysis)

        # Return response indicating update
        return Response({"analysis_id": instance.analysis_id})

    def destroy(self, request: Request, code: str, analysis_id: int) -> Response:
        """
        Use the `analysis_id` to permanently delete an analysis for the given project `code`.
        """

        # Get the instance to be deleted
        # If the instance does not exist, return 404
        try:
            instance = Analysis.objects.get(
                project=self.project, analysis_id=analysis_id
            )
        except Analysis.DoesNotExist:
            raise AnalysisIdNotFound

        # Delete the instance
        instance.delete()

        # Return response indicating deletion
        return Response({"analysis_id": analysis_id})


class AnalysisRecordsView(ProjectAPIView):
    permission_classes = ProjectApproved + [IsSiteMember]
    project_action = Actions.LIST

    def get(self, request: Request, code: str, analysis_id: str) -> Response:
        """
        Use the `analysis_id` to retrieve the records of an instance for the given project `code`.
        """

        # Check the instance exists
        # If the instance does not exist, return 404
        if not Analysis.objects.filter(
            project=self.project, analysis_id=analysis_id
        ).exists():
            raise AnalysisIdNotFound

        # Initial queryset
        qs = init_project_queryset(
            model=self.model,
            user=request.user,
            fields=self.handler.get_fields(),
        )

        # Filter the records with the analysis_id
        qs = qs.filter(analyses__analysis_id=analysis_id)

        # Serialize the results
        serializer = self.serializer_cls(
            qs,
            many=True,
            fields=unflatten_fields(self.handler.get_fields()),
        )

        # Return response with data
        return Response(serializer.data)
