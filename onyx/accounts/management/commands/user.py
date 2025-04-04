from typing import Optional
from django.core.management import base
from knox.models import AuthToken
from ...models import User, Site
from .utils import manage_instance_roles, manage_instance_groups, list_instances


ROLES = [
    "is_active",
    "is_approved",
    "is_staff",
]


class Command(base.BaseCommand):
    help = "Manage users."

    def add_arguments(self, parser):
        command = parser.add_subparsers(
            dest="command", metavar="{command}", required=True
        )
        parser.add_argument("--quiet", action="store_true")

        # CREATE A USER
        create_parser = command.add_parser("create", help="Create a user.")
        create_parser.add_argument("user")
        create_parser.add_argument("--site", required=True)
        create_parser.add_argument(
            "--password",
            required=False,
            help="If a password is not provided, the user is assigned a non-expiring token.",
        )

        # MANAGE USER ROLES
        roles_parser = command.add_parser("roles", help="Manage roles for a user.")
        roles_parser.add_argument("user")
        roles_parser.add_argument("-g", "--grant", nargs="+")
        roles_parser.add_argument("-r", "--revoke", nargs="+")

        # MANAGE USER GROUPS
        groups_parser = command.add_parser("groups", help="Manage groups for a user.")
        groups_parser.add_argument("user")
        groups_parser.add_argument("-g", "--grant", nargs="+")
        groups_parser.add_argument("-r", "--revoke", nargs="+")
        groups_parser.add_argument("--rxgrant")
        groups_parser.add_argument("--rxrevoke")

        # LIST USERS
        command.add_parser(
            "list",
            help="Print a table of all users, with their roles and project groups.",
        )

    def print(self, *args, **kwargs):
        if not self.quiet:
            print(*args, **kwargs)

    def handle(self, *args, **options):
        self.quiet = options["quiet"]

        if options["command"] == "create":
            self.create_user(
                username=options["user"],
                site=options["site"],
                password=options["password"],
            )
        elif options["command"] == "list":
            self.list_users()
        else:
            try:
                user = User.objects.get(username=options["user"])
            except User.DoesNotExist:
                self.print(f"User with username '{options['user']}' does not exist.")
                exit()

            self.print("User:", user.username)

            if options["command"] == "roles":
                granted, revoked = manage_instance_roles(
                    user,
                    ROLES,
                    options.get("grant"),
                    options.get("revoke"),
                )

                if granted:
                    self.print("Granted roles:")
                    for role in granted:
                        self.print(f"• {role}")

                if revoked:
                    self.print("Revoked roles:")
                    for role in revoked:
                        self.print(f"• {role}")

                if not granted and not revoked:
                    self.print("Roles:")
                    for role in ROLES:
                        self.print(f"• {role}: {getattr(user, role)}")

            elif options["command"] == "groups":
                granted, revoked = manage_instance_groups(
                    user,
                    options.get("grant"),
                    options.get("revoke"),
                    options.get("rxgrant"),
                    options.get("rxrevoke"),
                )

                if granted:
                    self.print("Granted groups:")
                    for group in granted:
                        self.print(f"• {group}")

                if revoked:
                    self.print("Revoked groups:")
                    for group in revoked:
                        self.print(f"• {group}")

                if not granted and not revoked:
                    self.print("Groups:")
                    for group in user.groups.all():
                        self.print(f"• {group.name}")

    def create_user(
        self,
        username: str,
        site: str,
        password: Optional[str] = None,
    ) -> None:
        """
        Create a user with the given username, site and optional password.

        If a password is not provided, the user is assigned a non-expiring token.

        Args:
            username: The username of the user.
            site: The code of the site.
            password: The password of the user.
        """

        # TODO: Functionality for updating a user

        if User.objects.filter(username=username).exists():
            self.print(f"User with username '{username}' already exists.")
            exit()

        if password:
            user = User.objects.create_user(  # type: ignore
                username=username,
                password=password,
                site=Site.objects.get(code=site),
            )
            self.print("Created user:", user.username)
            self.print(f"• Site: {user.site.code}")
        else:
            user = User.objects.create_user(  # type: ignore
                username=username,
                site=Site.objects.get(code=site),
            )
            user.set_unusable_password()
            user.save()
            _, token = AuthToken.objects.create(user, None)  #  type: ignore
            self.print("Created user:", user.username)
            self.print(f"• Site: {user.site.code}")
            self.print(f"• Token: {token}")

    def list_users(self) -> None:
        """
        Print a table of all users, with their roles and project groups.
        """

        list_instances(
            [
                {
                    "username": user.username,
                    "site": user.site.code,
                    "site_projects": ",".join(
                        user.site.projects.values_list("code", flat=True)
                    ),
                    "creator": user.creator.username if user.creator else None,
                    "date_joined": user.date_joined.strftime("%Y-%m-%d"),
                    "last_login": (
                        user.last_login.strftime("%Y-%m-%d")
                        if user.last_login
                        else None
                    ),
                    "is_active": user.is_active,
                    "is_approved": user.is_approved,
                    "is_staff": user.is_staff,
                    "groups": ",".join(user.groups.values_list("name", flat=True)),
                }
                for user in User.objects.all().order_by("-is_staff", "date_joined")
            ]
        )
