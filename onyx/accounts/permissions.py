from rest_framework import permissions, exceptions
from rest_framework.request import Request
from utils.functions import get_permission
from data.models import Project
from data.actions import Actions


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


class IsSiteMember(permissions.BasePermission):
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
    Allows access only to users who can perform the view's `project_action` on the `object_type` for the project they are accessing.
    """

    def has_permission(self, request: Request, view):
        # Get the project
        try:
            project = Project.objects.get(code__iexact=view.kwargs["code"])
        except Project.DoesNotExist:
            raise exceptions.NotFound

        # Check the user's permission to access the project
        access_permission = get_permission(
            app_label=project.content_type.app_label,
            action=Actions.ACCESS.label,
            code=project.code,
        )
        if not request.user.has_perm(access_permission):
            raise exceptions.NotFound

        # Check the user's site has access to the project
        if project not in request.user.site.projects.all():
            self.message = (
                f"Your site does not have access to the {project.name} project."
            )
            return False

        # Check the user's permission to access and perform action on the object type for the project
        for action in [Actions.ACCESS, view.project_action]:
            action_permission = get_permission(
                app_label=project.content_type.app_label,
                action=action.label,
                code=project.code,
                object_type=view.object_type.label,
            )
            if not request.user.has_perm(action_permission):
                self.message = f"You do not have permission to {action.description} {view.object_type.label} in the {project.name} project."
                return False

        # If the user has permission to access and perform the action on the project, then they have permission
        return True


# Useful permissions groupings
Any = [AllowAny]
Nobody = [AllowNobody]
Active = [IsAuthenticated, IsActiveSite, IsActiveUser]
Approved = Active + [IsApproved]
Admin = Approved + [IsAdminUser]
ProjectApproved = Approved + [IsProjectApproved]
