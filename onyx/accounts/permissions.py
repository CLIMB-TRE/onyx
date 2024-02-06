from rest_framework import permissions
from rest_framework.request import Request
from .exceptions import ProjectNotFound, ScopeNotFound
from utils.functions import get_suggestions, get_permission
from data.models import Project


class AllowAny(permissions.AllowAny):
    """
    Allow any access.
    """

    message = "You should be able to do this."


class AllowNobody(permissions.BasePermission):
    """
    Allow no access.
    """

    message = "This endpoint is closed."

    def has_permission(self, request: Request, view):
        return False


class IsAuthenticated(permissions.IsAuthenticated):
    """
    Allows access only to authenticated users.
    """

    message = "You need to provide authentication credentials."


class IsAdminUser(permissions.IsAdminUser):
    """
    Allows access only to admin users.
    """

    message = "You need to be an admin."


class IsActiveSite(permissions.BasePermission):
    """
    Allows access only to users who are still in an active site.
    """

    message = "Your site needs to be activated."

    def has_permission(self, request: Request, view):
        return bool(request.user and request.user.site and request.user.site.is_active)


class IsActiveUser(permissions.BasePermission):
    """
    Allows access only to users who are still active.
    """

    message = "Your account needs to be activated."

    def has_permission(self, request: Request, view):
        return bool(request.user and request.user.is_active)


class IsApproved(permissions.BasePermission):
    """
    Allows access only to users that have been approved.
    """

    message = "Your account needs to be approved."

    def has_permission(self, request: Request, view):
        return bool(
            request.user and (request.user.is_approved or request.user.is_staff)
        )


class IsObjectSite(permissions.BasePermission):
    """
    Allows access only to users of the same site as the object they are accessing.
    """

    message = "You need to be from the object's site."

    def has_object_permission(self, request: Request, view, obj):
        return bool(
            request.user
            and request.user.site
            and (request.user.site == obj.site or request.user.is_staff)
        )


class IsProjectApproved(permissions.BasePermission):
    """
    Allows access only to users who can perform action on the project + scopes they are accessing.
    """

    def has_permission(self, request: Request, view):
        # TODO: Add the project actions back as a list?
        # Get the project
        try:
            project = Project.objects.get(code__iexact=view.kwargs["code"])
        except Project.DoesNotExist:
            suggestions = get_suggestions(
                view.kwargs["code"],
                options=(
                    request.user.groups.values_list(
                        "projectgroup__project__code", flat=True
                    ).distinct()
                ),
                n=1,
                message_prefix="Project not found.",
            )
            raise ProjectNotFound(suggestions)

        # Check the user's permission to access the project
        project_access_permission = get_permission(
            app_label=project.content_type.app_label,
            action="access",
            code=project.code,
        )

        if not request.user.has_perm(project_access_permission):
            suggestions = get_suggestions(
                view.kwargs["code"],
                options=(
                    request.user.groups.values_list(
                        "projectgroup__project__code", flat=True
                    ).distinct()
                ),
                n=1,
                message_prefix="Project not found.",
            )
            raise ProjectNotFound(suggestions)

        # Check the user's permission to perform action on the project
        project_action_permission = get_permission(
            app_label=project.content_type.app_label,
            action=view.project_action,
            code=project.code,
        )

        if not request.user.has_perm(project_action_permission):
            self.message = f"You do not have permission to perform action '{view.project_action}' on project '{project.code}'."
            return False

        # If the user has permission to access and perform action on the project, then they have permission
        return True


# Useful permissions groupings
Any = [AllowAny]
Nobody = [AllowNobody]
Active = [IsAuthenticated, IsActiveSite, IsActiveUser]
Approved = Active + [IsApproved]
Admin = Approved + [IsAdminUser]
ProjectApproved = Approved + [IsProjectApproved]
ProjectAdmin = Admin + [IsProjectApproved]
