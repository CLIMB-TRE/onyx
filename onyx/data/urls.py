from django.urls import include, path, re_path
from django.urls.resolvers import URLResolver
from . import views
from .serializers import ProjectRecordSerializer, ProjectAnalysisSerializer


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
    code: str,
    serializer_class: type[ProjectRecordSerializer],
    analysis_serializer_class: type[ProjectAnalysisSerializer] | None = None,
) -> URLResolver:
    """
    Generate the URL patterns for a project.

    Args:
        code: The project code.
        serializer_class: The serializer class for the project.

    Returns:
        A list of URL patterns.
    """

    project_patterns = [
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
            r"^history/(?P<climb_id>[cC]-[a-zA-Z0-9]{10})/$",
            views.HistoryView.as_view(),
            name=f"projects.{code}.history.climb_id",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
        re_path(
            r"^identify/(?P<field>[a-zA-Z0-9_]*)/$",
            views.IdentifyView.as_view(),
            name=f"projects.{code}.identify.field",
            kwargs={"code": code, "serializer_class": serializer_class},
        ),
    ]

    if analysis_serializer_class:
        project_patterns.extend(
            [
                re_path(
                    r"^analysis/$",
                    views.ProjectAnalysisViewSet.as_view(
                        {"post": "create", "get": "list"}
                    ),
                    name=f"projects.{code}.analysis",
                    kwargs={
                        "code": code,
                        "serializer_class": serializer_class,
                        "analysis_serializer_class": analysis_serializer_class,
                    },
                ),
                re_path(
                    r"^analysis/(?P<analysis_id>[aA]-[a-zA-Z0-9]{10})/$",
                    views.ProjectAnalysisViewSet.as_view(
                        {
                            "get": "retrieve",
                            "patch": "partial_update",
                            "delete": "destroy",
                        }
                    ),
                    name=f"projects.{code}.analysis.analysis_id",
                    kwargs={
                        "code": code,
                        "serializer_class": serializer_class,
                        "analysis_serializer_class": analysis_serializer_class,
                    },
                ),
            ]
        )

    return path(f"{code}/", include(project_patterns))
