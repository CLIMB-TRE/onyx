from rest_framework import status
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication
from knox.views import LoginView as KnoxLoginView
from datetime import datetime
from .models import User
from .serializers import (
    UserSerializer,
    SiteWaitingUserSerializer,
    AdminWaitingUserSerializer,
)
from utils.response import OnyxResponse
from utils.views import OnyxAPIView, OnyxCreateAPIView, OnyxListAPIView
from .permissions import (
    Any,
    Admin,
    ApprovedOrAdmin,
    SiteAuthorityOrAdmin,
    SameSiteAuthorityAsUserOrAdmin,
)


def create_username(first_name, last_name):
    return f"{last_name}{first_name[:1]}"


class LoginView(KnoxLoginView):
    """
    Login a user.
    """

    authentication_classes = [BasicAuthentication]


class CreateUserView(OnyxCreateAPIView):
    """
    Create a user.
    """

    permission_classes = Any
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def post(self, request, *args, **kwargs):
        errors = {}

        if not request.data.get("first_name"):
            errors["first_name"] = ["This field is required."]

        elif not request.data.get("first_name").isalpha():
            errors["first_name"] = [
                "This field must only contain alphabetic characters."
            ]

        if not request.data.get("last_name"):
            errors["last_name"] = ["This field is required."]

        elif not request.data.get("last_name").isalpha():
            errors["last_name"] = [
                "This field must only contain alphabetic characters."
            ]

        if errors:
            return OnyxResponse.validation_error(errors)

        # Enable mutability if required
        mutable = getattr(request.data, "_mutable", None)

        if mutable is not None:
            mutable = request.data._mutable
            request.data._mutable = True

        # Create username and add to the request
        request.data["username"] = create_username(
            request.data["first_name"], request.data["last_name"]
        )

        if mutable is not None:
            request.data._mutable = mutable

        # Create the user
        return super().post(request, *args, **kwargs)


class SiteApproveView(OnyxAPIView):
    """
    Grant site approval to a user.
    """

    permission_classes = SameSiteAuthorityAsUserOrAdmin

    def patch(self, request, username):
        # Get user to be approved
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return OnyxResponse.not_found("user")

        # Approve user
        user.is_site_approved = True
        user.when_site_approved = datetime.now()
        user.save(update_fields=["is_site_approved", "when_site_approved"])

        return Response(
            {
                "username": username,
                "is_site_approved": user.is_site_approved,
            },
            status=status.HTTP_200_OK,
        )


class AdminApproveView(OnyxAPIView):
    """
    Grant admin approval to a user.
    """

    permission_classes = Admin

    def patch(self, request, username):
        # Get user to be approved
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return OnyxResponse.not_found("user")

        # Approve target user
        user.is_admin_approved = True
        user.when_admin_approved = datetime.now()
        user.save(update_fields=["is_admin_approved", "when_admin_approved"])

        return Response(
            {
                "username": username,
                "is_admin_approved": user.is_admin_approved,
            },
            status=status.HTTP_200_OK,
        )


class SiteWaitingView(OnyxListAPIView):
    """
    List all users waiting for site approval.
    """

    permission_classes = SiteAuthorityOrAdmin
    serializer_class = SiteWaitingUserSerializer

    def get_queryset(self):
        if self.request.user.is_staff:  # type: ignore
            return (
                User.objects.filter(is_active=True)
                .filter(is_site_approved=False)
                .order_by("-date_joined")
            )
        else:
            return (
                User.objects.filter(is_active=True)
                .filter(site=self.request.user.site)  # type: ignore
                .filter(is_site_approved=False)
                .order_by("-date_joined")
            )


class AdminWaitingView(OnyxListAPIView):
    """
    List all users waiting for admin approval.
    """

    permission_classes = Admin
    serializer_class = AdminWaitingUserSerializer

    def get_queryset(self):
        return (
            User.objects.filter(is_active=True)
            .filter(is_site_approved=True)
            .filter(is_admin_approved=False)
            .order_by("-when_site_approved")
        )


class SiteUsersView(OnyxListAPIView):
    """
    List all users in the site of the requesting user.
    """

    permission_classes = ApprovedOrAdmin
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.filter(site=self.request.user.site).order_by("-date_joined")  # type: ignore


class AdminUsersView(OnyxListAPIView):
    """
    List all users.
    """

    permission_classes = Admin
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.order_by("-date_joined")