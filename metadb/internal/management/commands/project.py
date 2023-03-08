from django.core.management import base
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from ...models import Project
from utils.groups import read_groups, create_or_update_group


class Command(base.BaseCommand):
    help = "Create or update a project in the database."

    def add_arguments(self, parser):
        parser.add_argument("code")
        parser.add_argument("--content-type")
        parser.add_argument("--groups")
        visibility = parser.add_mutually_exclusive_group(required=True)
        visibility.add_argument("--public", action="store_false", dest="hidden")
        visibility.add_argument("--private", action="store_true", dest="hidden")

    def handle(self, *args, **options):
        code = options["code"].lower()
        app, model = options["content_type"].split(".")
        content_type = ContentType.objects.get(app_label=app, model=model)
        groups = {}

        for gdef in read_groups(options["groups"]):
            group, created = create_or_update_group(gdef)

            action, _, _ = gdef.name.partition("_")
            action_perm, _ = Permission.objects.get_or_create(
                codename=f"{action}_{code}",
                name=f"Can {action} {code}",
                content_type=content_type,
            )
            group.permissions.add(action_perm)

            groups[action] = group

            if created:
                print(f"Group created: {gdef.name}")
            else:
                print(f"Group updated: {gdef.name}")

            print("Permissions:")
            for perm in group.permissions.all():
                print(perm)

        project, created = Project.objects.update_or_create(
            code=code,
            defaults={
                "hidden": options["hidden"],
                "content_type": content_type,
                "add_group": groups["add"],
                "view_group": groups["view"],
                "change_group": groups["change"],
                "suppress_group": groups["suppress"],
                "delete_group": groups["delete"],
            },
        )

        if created:
            print("Project created.")
        else:
            print("Project updated.")

        print("Code:", project.code)
        print("Model:", project.content_type.model_class())
        print("Hidden:", project.hidden)
