from django.urls import path, re_path
from django.urls.resolvers import URLPattern
from . import views
from .serializers import ProjectRecordSerializer


urlpatterns = [
    path(
        "",
        views.ProjectsView.as_view(),
        name="data.projects",
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
            r"",
            views.ProjectRecordsViewSet.as_view({"post": "create", "get": "list"}),
            name=f"project.{code}",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
        re_path(
            r"^(?P<climb_id>[cC]-[a-zA-Z0-9]{10})/$",
            views.ProjectRecordsViewSet.as_view(
                {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
            ),
            name=f"project.{code}.climb_id",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
        re_path(
            r"^test/$",
            views.ProjectRecordsViewSet.as_view({"post": "create"}),
            name=f"project.{code}.test",
            kwargs={"code": code, "serializer_class": serializer_class, "test": True},
        ),
        re_path(
            r"^test/(?P<climb_id>[cC]-[a-zA-Z0-9]{10})/$",
            views.ProjectRecordsViewSet.as_view({"patch": "partial_update"}),
            name=f"project.{code}.test.climb_id",
            kwargs={"code": code, "serializer_class": serializer_class, "test": True},
        ),
        re_path(
            r"^query/$",
            views.ProjectRecordsViewSet.as_view({"post": "list"}),
            name=f"project.{code}.query",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
        re_path(
            r"^fields/$",
            views.FieldsView.as_view(),
            name=f"project.{code}.fields",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
        re_path(
            r"^lookups/$",
            views.LookupsView.as_view(),
            name=f"project.{code}.lookups",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
        re_path(
            r"^choices/(?P<field>[a-zA-Z0-9_]*)/$",
            views.ChoicesView.as_view(),
            name=f"project.{code}.choices",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
        re_path(
            r"^identify/(?P<field>[a-zA-Z0-9_]*)/$",
            views.IdentifyView.as_view(),
            name=f"project.{code}.identify",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
    ]
