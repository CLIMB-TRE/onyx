from typing import Optional
from django.core.management import base
from ...models import Site
from .utils import manage_instance_roles, list_instances


ROLES = [
    "is_active",
]


def create_site(
    code: str,
    description: Optional[str] = None,
) -> None:
    """
    Create/update a site with the given code and description.
    
    Args:
        code: The code of the site.
        description: The description of the site.
    """

    defaults = {}

    if description:
        defaults["description"] = description

    site, created = Site.objects.update_or_create(
        code=code.lower(),
        defaults=defaults,
    )

    if created:
        print(f"Created site: {site.code}")
    else:
        print(f"Updated site: {site.code}")

    print(f"• Description: {site.description}")


def list_sites():
    """
    Print a table of all sites, with their roles.
    """

    list_instances(
        [
            {
                "code": site.code,
                "is_active": site.is_active,
                "description": f"'{site.description}'",
            }
            for site in Site.objects.all()
        ]
    )


class Command(base.BaseCommand):
    help = "Manage sites."

    def add_arguments(self, parser):
        command = parser.add_subparsers(
            dest="command", metavar="{command}", required=True
        )

        # CREATE A SITE
        create_parser = command.add_parser("create", help="Create a site.")
        create_parser.add_argument("code")
        create_parser.add_argument("-d", "--description")

        # MANAGE SITE ROLES
        roles_parser = command.add_parser("roles", help="Manage roles for a site.")
        roles_parser.add_argument("code")
        roles_parser.add_argument("-g", "--grant", nargs="+")
        roles_parser.add_argument("-r", "--revoke", nargs="+")

        # LIST SITES
        list_parser = command.add_parser(
            "list", help="Print a table of all sites, with their roles."
        )

    def handle(self, *args, **options):
        if options["command"] == "create":
            create_site(
                code=options["code"],
                description=options["description"],
            )

        elif options["command"] == "list":
            list_sites()

        else:
            try:
                site = Site.objects.get(code=options["code"])
            except Site.DoesNotExist:
                print(f"Site with code '{options["code"]}' does not exist.")
                exit()
            
            print("Site:", site.code)

            if options["command"] == "roles":
                granted, revoked = manage_instance_roles(
                    site,
                    ROLES,
                    granted=options.get("grant"),
                    revoked=options.get("revoke"),
                )

                if granted:
                    print("Granted roles:")
                    for role in granted:
                        print(f"• {role}")
                
                if revoked:
                    print("Revoked roles:")
                    for role in revoked:
                        print(f"• {role}")

                if not granted and not revoked:
                    print("Roles:")
                    for role in ROLES:
                        print(f"• {role}: {getattr(site, role)}")       
