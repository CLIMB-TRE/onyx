from django.contrib.auth.models import Group
from rest_framework import exceptions
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
        # Filter and return all active, approved users for the site
        assert isinstance(self.request.user, User)
        return User.objects.filter(
            is_active=True,
            is_approved=True,
            site=self.request.user.site,
        ).order_by("-date_joined")


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

    def post(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed(self.request.method)

    def get(self, request, code, site_code, username):
        # Get the base view group for the requested project
        try:
            view_group = Group.objects.get(
                projectgroup__project__code=code,
                projectgroup__action="view",
                projectgroup__scope="base",
            )
        except Group.DoesNotExist:
            raise ProjectNotFound

        # Get the requested site
        try:
            site = Site.objects.get(code=site_code)
        except Site.DoesNotExist:
            raise SiteNotFound

        # Get the user, and check they have the correct creator and site
        # If the user does not exist, create them
        try:
            user = User.objects.get(username=username)
            if user.creator != request.user:
                raise exceptions.PermissionDenied(
                    {"detail": "This user cannot be modified."}
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

        user.groups.add(view_group)

        request.user = user
        return super().post(request)
