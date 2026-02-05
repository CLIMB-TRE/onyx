from typing import Optional
from django.core.management import base
from data.models import Project
from ...models import Site
from .utils import manage_instance_roles, list_instances


ROLES = [
    "is_active",
]


def create_site(
    self,
    code: str,
    description: Optional[str] = None,
    projects: Optional[list[str]] = None,
) -> None:
    """
    Create/update a site with the given code and description.

    Args:
        code: The code of the site.
        description: The description of the site.
        projects: A list of project codes for projects the site can access.
    """

    defaults = {}

    if description:
        defaults["description"] = description

    site, created = Site.objects.update_or_create(
        code=code.lower(),
        defaults=defaults,
    )

    project_instances = []

    if projects:
        for project in projects:
            try:
                project_instance = Project.objects.get(code=project)
            except Project.DoesNotExist:
                self.print(f"Project with code '{project}' does not exist.")
                exit()
            project_instances.append(project_instance)

    site.projects.set(project_instances)

    if created:
        self.print(f"Created site: {site.code}")
    else:
        self.print(f"Updated site: {site.code}")

    self.print(f"• Description: {site.description}")
    self.print(f"• Projects: {', '.join(site.projects.values_list('name', flat=True))}")


class Command(base.BaseCommand):
    help = "Manage sites."

    def add_arguments(self, parser):
        command = parser.add_subparsers(
            dest="command", metavar="{command}", required=True
        )
        parser.add_argument("--quiet", action="store_true")

        # CREATE A SITE
        create_parser = command.add_parser("create", help="Create a site.")
        create_parser.add_argument("code")
        create_parser.add_argument("-d", "--description")
        create_parser.add_argument("-p", "--projects", nargs="+")

        # MANAGE SITE ROLES
        roles_parser = command.add_parser("roles", help="Manage roles for a site.")
        roles_parser.add_argument("code")
        roles_parser.add_argument("-g", "--grant", nargs="+")
        roles_parser.add_argument("-r", "--revoke", nargs="+")

        # LIST SITES
        command.add_parser("list", help="Print a table of all sites, with their roles.")

    def print(self, *args, **kwargs):
        if not self.quiet:
            print(*args, **kwargs)

    def handle(self, *args, **options):
        self.quiet = options["quiet"]

        if options["command"] == "create":
            create_site(
                self,
                code=options["code"],
                description=options["description"],
                projects=options["projects"],
            )

        elif options["command"] == "list":
            self.list_sites()

        else:
            try:
                site = Site.objects.get(code=options["code"])
            except Site.DoesNotExist:
                self.print(f"Site with code '{options['code']}' does not exist.")
                exit()

            self.print("Site:", site.code)

            if options["command"] == "roles":
                granted, revoked = manage_instance_roles(
                    site,
                    ROLES,
                    granted=options.get("grant"),
                    revoked=options.get("revoke"),
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
                        self.print(f"• {role}: {getattr(site, role)}")

    def list_sites(self):
        """
        Print a table of all sites, with their roles.
        """

        list_instances(
            [
                {
                    "code": site.code,
                    "description": f"'{site.description.replace(' ', '+')}'",
                    "is_active": site.is_active,
                    "projects": ",".join(site.projects.values_list("code", flat=True)),
                }
                for site in Site.objects.all()
            ]
        )
