import json
from typing import Optional, List
from pydantic import BaseModel
from django.core.management import base
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from ...models import Project, ProjectGroup, Choice


class GroupConfig(BaseModel):
    action: str
    scope: str
    fields: List[str]


class ChoiceConfig(BaseModel):
    field: str
    options: List[str]


class ChoiceConstraintConfig(BaseModel):
    field: str
    option: str
    constraints: List[ChoiceConfig]


class ProjectConfig(BaseModel):
    code: str
    name: Optional[str]
    description: Optional[str]
    content_type: Optional[str]
    groups: Optional[List[GroupConfig]]
    choices: Optional[List[ChoiceConfig]]
    choice_constraints: Optional[List[ChoiceConstraintConfig]]


class Command(base.BaseCommand):
    help = "Create/manage projects."

    def add_arguments(self, parser):
        parser.add_argument("project_config")
        parser.add_argument("--quiet", action="store_true")

    def print(self, *args, **kwargs):
        if not self.quiet:
            print(*args, **kwargs)

    def handle(self, *args, **options):
        self.quiet = options["quiet"]

        with open(options["project_config"]) as project_config_file:
            project_config = ProjectConfig.model_validate(
                json.load(project_config_file)
            )

        self.set_project(project_config)

    def set_project(self, project_config: ProjectConfig):
        """
        Create/update the project.
        """

        # If a {app}.{model} was provided, use it to get the content_type
        # Otherwise, assume that app = data and that the model has the same name as the project
        if project_config.content_type:
            app, _, model = project_config.content_type.partition(".")
        else:
            app, model = "data", project_config.code

        self.project, p_created = Project.objects.update_or_create(
            code=project_config.code,
            defaults={
                # If no name was provided, use the code
                "name": project_config.name
                if project_config.name
                else project_config.code,
                # If no description was provided, set as empty
                "description": project_config.description
                if project_config.description
                else "",
                "content_type": ContentType.objects.get(app_label=app, model=model),
            },
        )

        if p_created:
            self.print(f"Creating project: {self.project.code}")
        else:
            self.print(f"Updating project: {self.project.code}")

        if project_config.groups:
            self.set_groups(project_config.groups)

        if project_config.choices:
            self.set_choices(project_config.choices)

        if project_config.choice_constraints:
            self.set_choice_constraints(project_config.choice_constraints)

        if p_created:
            self.print(f"Successfully created project: {self.project.code}")
        else:
            self.print(f"Successfully updated project: {self.project.code}")

        self.print("Name:", self.project.name)
        self.print("Description:", self.project.description)
        self.print("Model:", self.project.content_type.model_class())

    def set_groups(self, group_configs: List[GroupConfig]):
        """
        Create/update the groups for the project.
        """

        groups = {}

        for group_config in group_configs:
            # Create or retrieve underlying permissions group
            # This is based on project code, action and scope
            name = f"{self.project.code}.{group_config.action}.{group_config.scope}"
            group, g_created = Group.objects.get_or_create(name=name)

            if g_created:
                self.print(f"Created group: {name}")
            else:
                self.print(f"Updated group: {name}")

            # Create or retrieve permissions for the group from the fields within the data
            permissions = []
            for field in group_config.fields:
                codename = f"{group_config.action}_{self.project.code}__{field}"
                permission, p_created = Permission.objects.get_or_create(
                    content_type=self.project.content_type,
                    codename=codename,
                    name=f"Can {group_config.action} {self.project.code}{' ' + field if field else ''}",
                )
                if p_created:
                    self.print("Created permission:", permission)

                permissions.append(permission)

            # Set permissions for the group, and print them if they exist
            group.permissions.set(permissions)
            if permissions:
                self.print(f"Permissions for {name}:")
                for perm in group.permissions.all():
                    self.print(f"\t{perm}")
            else:
                self.print(f"Group {name} has no permissions.")

            # Add the group to the groups structure
            groups[(group_config.action, group_config.scope)] = group

        # Create/update the corresponding project group for each group
        for (action, scope), group in groups.items():
            projectgroup, pg_created = ProjectGroup.objects.update_or_create(
                group=group,
                defaults={"project": self.project, "action": action, "scope": scope},
            )
            if pg_created:
                self.print(
                    f"Created project group: {self.project.code} | {projectgroup.action} | {projectgroup.scope}"
                )
            else:
                self.print(
                    f"Updated project group: {self.project.code} | {projectgroup.action} | {projectgroup.scope}"
                )

    def set_choices(self, choice_configs: List[ChoiceConfig]):
        """
        Create/update the choices for the project.
        """

        # TODO: Issue with reactivate/deactivate choices if you provide them in uppercase in the json
        # Upgrade Choices management command to DELETE inactive choices if a new one comes in with the same characters but a different case
        # E.g. if a new choice Swab comes in, DELETE the old choice swab
        # TL:DR we need case insensitivity in handling

        for choice_config in choice_configs:
            # Create new choices if required
            for option in choice_config.options:
                instance, created = Choice.objects.get_or_create(
                    project_id=self.project.code,
                    field=choice_config.field,
                    choice=option,
                )

                if created:
                    self.print(
                        f"Created choice: {self.project.code} | {instance.field} | {instance.choice}",
                    )
                elif not instance.is_active:
                    instance.is_active = True
                    instance.save()
                    self.print(
                        f"Reactivated choice: {self.project.code} | {instance.field} | {instance.choice}",
                    )
                else:
                    self.print(
                        f"Active choice: {self.project.code} | {instance.field} | {instance.choice}",
                    )

            # Deactivate choices no longer in the set
            instances = Choice.objects.filter(
                project_id=self.project.code,
                field=choice_config.field,
                is_active=True,
            )

            for instance in instances:
                if instance.choice not in choice_config.options:
                    instance.is_active = False
                    instance.save()
                    self.print(
                        f"Deactivated choice: {self.project.code} | {instance.field} | {instance.choice}",
                    )

    def set_choice_constraints(
        self, choice_constraint_configs: List[ChoiceConstraintConfig]
    ):
        """
        Create/update the choice constraints for the project.
        """

        # TODO: Case insensitivity in constraint handling

        # Empty constraints for the project
        for choice in Choice.objects.filter(project_id=self.project.code):
            choice.constraints.clear()

        for choice_constraint_config in choice_constraint_configs:
            choice_instance = Choice.objects.get(
                project_id=self.project.code,
                field=choice_constraint_config.field,
                choice=choice_constraint_config.option,
            )

            for constraint in choice_constraint_config.constraints:
                # Get each constraint choice instance
                constraint_instances = [
                    Choice.objects.get(
                        project_id=self.project.code,
                        field=constraint.field,
                        choice=constraint_option,
                    )
                    for constraint_option in constraint.options
                ]

                # Set constraints
                # This is set both ways: each constraint is added for the choice
                # And the choice is added for each constraint
                for constraint_instance in constraint_instances:
                    choice_instance.constraints.add(constraint_instance)
                    constraint_instance.constraints.add(choice_instance)
                    self.print(
                        f"Set constraint: {self.project.code} | ({choice_instance.field}, {choice_instance.choice}) | ({constraint_instance.field}, {constraint_instance.choice})",
                    )

        # Check that each constraint in a choice's constraint set also has the choice itself as a constraint
        valid = True
        for choice in Choice.objects.all():
            for constraint in choice.constraints.all():
                if choice not in constraint.constraints.all():
                    self.print(
                        f"Choice {(choice.field, choice.choice)} is not in the constraint set of Choice {(constraint.field, constraint.choice)}.",
                    )
                    valid = False
                    break

        if valid:
            self.print("Constraints are valid.")
        else:
            self.print("Constraints are invalid.")
