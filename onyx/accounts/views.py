from django.contrib.auth.models import Group
from rest_framework import exceptions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, ListAPIView
from knox.views import LoginView as KnoxLoginView
import internal.models
from internal.serializers import RequestSerializer
from .models import User, Site
from .serializers import (
    RegisterSerializer,
    ViewUserSerializer,
    WaitingUserSerializer,
)
from .permissions import Nobody, Approved, Admin
from .exceptions import ProjectNotFound, UserNotFound, SiteNotFound


class RegisterView(CreateAPIView):
    """
    Register a user.
    """

    permission_classes = Nobody
    serializer_class = RegisterSerializer
    queryset = User.objects.all()


class LoginView(KnoxLoginView):
    """
    Login a user.
    """

    permission_classes = Approved
    authentication_classes = [BasicAuthentication]


class ProfileView(APIView):
    """
    View the user's information.
    """

    permission_classes = Approved

    def get(self, request):
        # Serialize and return the user's profile information
        serializer = ViewUserSerializer(instance=request.user)
        return Response(serializer.data)


class ActivityView(ListAPIView):
    """
    View the user's latest activity.
    """

    permission_classes = Approved
    serializer_class = RequestSerializer

    def get_queryset(self):
        assert isinstance(self.request.user, User)

        activity = reversed(
            internal.models.Request.objects.filter(
                user=self.request.user,
            ).order_by(
                "-date"
            )[:50]
        )

        return activity


class WaitingUsersView(ListAPIView):
    """
    List users waiting for approval.
    """

    permission_classes = Admin
    serializer_class = WaitingUserSerializer

    def get_queryset(self):
        # Filter and return all active but unapproved users
        return User.objects.filter(is_active=True, is_approved=False).order_by(
            "-date_joined"
        )


class ApproveUserView(APIView):
    """
    Approve a user.
    """

    permission_classes = Admin

    def patch(self, request, username):
        # Get the user to be approved (they must be active)
        try:
            user = User.objects.get(is_active=True, username=username)
        except User.DoesNotExist:
            raise UserNotFound

        # Approve the user
        user.is_approved = True
        user.save()

        return Response(
            {
                "username": username,
                "is_approved": user.is_approved,
            },
        )


class SiteUsersView(ListAPIView):
    """
    List users in the site of the requesting user.
    """

    permission_classes = Approved
    serializer_class = ViewUserSerializer

    def get_queryset(self):
        assert isinstance(self.request.user, User)

        # Filter and return all active, approved users for the site
        # who have access to the same projects
        projects = self.request.user.groups.values_list(
            "projectgroup__project", flat=True
        ).distinct()

        users = User.objects.filter(
            is_active=True,
            is_approved=True,
            site=self.request.user.site,
            groups__projectgroup__project__in=projects,
        ).order_by("-date_joined")

        return users


class AllUsersView(ListAPIView):
    """
    List all users.
    """

    permission_classes = Admin
    serializer_class = ViewUserSerializer

    def get_queryset(self):
        # Filter and return all users
        return User.objects.order_by("-date_joined")


class ProjectUserView(KnoxLoginView):
    """
    Create/retrieve a user with permission to view a specific project.
    """

    permission_classes = Admin

    def post(self, request: Request, project_code: str, site_code: str, username: str):
        # Get the analyst group for the project
        try:
            analyst_group = Group.objects.get(
                projectgroup__project__code=project_code,
                projectgroup__scope="analyst",
            )
        except Group.DoesNotExist:
            raise ProjectNotFound

        # Get the project
        project = analyst_group.projectgroup.project  #  type: ignore

        # Get the site
        try:
            site = Site.objects.get(code=site_code)
        except Site.DoesNotExist:
            raise SiteNotFound

        # The site must have access to the project
        if project not in site.projects.all():
            raise exceptions.PermissionDenied(
                {"detail": "This site does not have access to this project."}
            )

        # Get the user, and check they have the correct creator and site
        # If the user does not exist, create them
        try:
            user = User.objects.get(username=username)
            if user.creator != request.user or user == request.user:
                raise exceptions.PermissionDenied(
                    {"detail": "You cannot modify this user."}
                )
            if user.site != site:
                raise exceptions.ValidationError(
                    {"detail": "This user belongs to a different site."}
                )
        except User.DoesNotExist:
            user = User.objects.create(
                username=username,
                site=site,
                is_approved=True,
                creator=request.user,
            )
            user.set_unusable_password()
            user.save()

        # Add the user to the analyst group
        user.groups.add(analyst_group)

        request.user = user
        return super().post(request)
