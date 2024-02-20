from django.contrib.auth.models import Group
from django.db import transaction
from rest_framework import exceptions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, ListAPIView
from knox.views import LoginView as KnoxLoginView
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
        qs = User.objects.filter(
            is_active=True,
            is_approved=True,
            site=self.request.user.site,
        )

        # If the requesting user is a project user, filter by project
        if self.request.user.is_projectuser:
            qs = qs.filter(project=self.request.user.project)

        return qs.order_by("-date_joined")


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

    def post(self, request: Request, *args, **kwargs):
        # TODO: Change method back to POST
        raise exceptions.MethodNotAllowed(self.request.method)

    def get(self, request: Request, code: str, site_code: str, username: str):
        # Get the analyst group for the requested project
        try:
            analyst_group = Group.objects.get(
                projectgroup__project__code=code,
                projectgroup__scope="analyst",
            )
        except Group.DoesNotExist:
            raise ProjectNotFound

        # Attempt to parse site code from username
        # TODO: Sort out CLIMB configuration so this is not needed
        try:
            _, tenant = username.split(".")
            site_code = tenant.split("-")[-2]
        except Exception:
            pass

        # Get the requested site
        try:
            site = Site.objects.get(code=site_code)
        except Site.DoesNotExist:
            raise SiteNotFound

        try:
            # Get the projectuser
            user = User.objects.get(username=username)

            # The user cannot be the creator, or have a different creator
            if user.creator != request.user or user == request.user:
                raise exceptions.PermissionDenied(
                    {"detail": "You cannot modify this user."}
                )

            # The user cannot be from a different site than specified
            if user.site != site:
                raise exceptions.ValidationError(
                    {"detail": "This user belongs to a different site."}
                )

            # The user must be a projectuser
            if not user.is_projectuser:
                raise exceptions.PermissionDenied(
                    {"detail": "This user is not a projectuser."}
                )

            # The user cannot be from a different project than specified
            if user.project != analyst_group.projectgroup.project:  #  type: ignore
                raise exceptions.ValidationError(
                    {"detail": "This user belongs to a different project."}
                )

        except User.DoesNotExist:
            # If the user does not exist, create them and add them to the analyst group
            with transaction.atomic():
                user = User.objects.create(
                    username=username,
                    site=site,
                    is_approved=True,
                    creator=request.user,
                    is_projectuser=True,
                    project=analyst_group.projectgroup.project,  #  type: ignore
                )
                user.set_unusable_password()
                user.save()
                user.groups.set([analyst_group])

        request.user = user
        return super().post(request)
