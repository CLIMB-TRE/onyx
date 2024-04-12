from django.urls import path, re_path
from django.urls.resolvers import URLPattern
from . import views
from .serializers import ProjectRecordSerializer


urlpatterns = [
    path(
        "",
        views.ProjectsView.as_view(),
        name="projects",
    ),
    path(
        "types/",
        views.TypesView.as_view(),
        name=f"projects.types",
    ),
    path(
        "lookups/",
        views.LookupsView.as_view(),
        name=f"projects.lookups",
    ),
]


def generate_project_urls(
    code: str, serializer_class: type[ProjectRecordSerializer]
) -> list[URLPattern]:
    """
    Generate the URL patterns for a project.

    Args:
        code: The project code.
        serializer_class: The serializer class for the project.

    Returns:
        A list of URL patterns.
    """

    return [
        path(
            "",
            views.ProjectRecordsViewSet.as_view({"post": "create", "get": "list"}),
            name=f"projects.{code}",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
        re_path(
            r"^(?P<climb_id>[cC]-[a-zA-Z0-9]{10})/$",
            views.ProjectRecordsViewSet.as_view(
                {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
            ),
            name=f"projects.{code}.climb_id",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
        path(
            "test/",
            views.ProjectRecordsViewSet.as_view({"post": "create"}),
            name=f"projects.{code}.test",
            kwargs={"code": code, "serializer_class": serializer_class, "test": True},
        ),
        re_path(
            r"^test/(?P<climb_id>[cC]-[a-zA-Z0-9]{10})/$",
            views.ProjectRecordsViewSet.as_view({"patch": "partial_update"}),
            name=f"projects.{code}.test.climb_id",
            kwargs={"code": code, "serializer_class": serializer_class, "test": True},
        ),
        path(
            "query/",
            views.ProjectRecordsViewSet.as_view({"post": "list"}),
            name=f"projects.{code}.query",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
        path(
            "fields/",
            views.FieldsView.as_view(),
            name=f"projects.{code}.fields",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
        re_path(
            r"^choices/(?P<field>[a-zA-Z0-9_]*)/$",
            views.ChoicesView.as_view(),
            name=f"projects.{code}.choices.field",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
        re_path(
            r"^identify/(?P<field>[a-zA-Z0-9_]*)/$",
            views.IdentifyView.as_view(),
            name=f"projects.{code}.identify.field",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
    ]
