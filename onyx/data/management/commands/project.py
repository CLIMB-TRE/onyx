import json
from typing import Optional, List, Union
from pydantic import BaseModel, field_validator
from django.core.management import base
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from ...models import Project, ProjectGroup, Choice
from ...actions import Actions


ACTION_LABELS = [action.label for action in Actions]


class PermissionConfig(BaseModel):
    action: str | List[str]
    fields: List[str]

    @field_validator("action")
    def validate_action(cls, value):
        if isinstance(value, str):
            assert value in ACTION_LABELS, f"Invalid action: {value}"
        else:
            for v in value:
                assert v in ACTION_LABELS, f"Invalid action: {v}"

        return value


class GroupConfig(BaseModel):
    scope: str
    permissions: List[PermissionConfig]


class ChoiceInfoConfig(BaseModel):
    choice: str
    description: str


class ChoiceConfig(BaseModel):
    field: str
    options: List[Union[str, ChoiceInfoConfig]]


class ChoiceConstraintConfig(BaseModel):
    field: str
    option: str
    constraints: List[ChoiceConfig]


class ProjectConfig(BaseModel):
    code: str
    name: Optional[str]
    description: Optional[str]
    content_type: str
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

        # Get the app and model from the content type
        app, _, model = project_config.content_type.partition(".")

        # Create or retrieve the project
        self.project, p_created = Project.objects.update_or_create(
            code=project_config.code,
            defaults={
                # If no name was provided, use the code
                "name": (
                    project_config.name if project_config.name else project_config.code
                ),
                # If no description was provided, set as empty
                "description": (
                    project_config.description if project_config.description else ""
                ),
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
            self.print(f"Created project: {self.project.code}")
        else:
            self.print(f"Updated project: {self.project.code}")

        self.print("• Name:", self.project.name)
        self.print("• Description:", self.project.description)
        self.print("• Model:", self.project.content_type.model_class())

    def set_groups(self, group_configs: List[GroupConfig]):
        """
        Create/update the groups for the project.
        """

        groups = {}

        for group_config in group_configs:
            # Create or retrieve underlying permissions group
            # This is based on project code and scope
            name = f"{self.project.code}.{group_config.scope}"
            group, g_created = Group.objects.get_or_create(name=name)

            if g_created:
                self.print(f"Created group: {name}")
            else:
                self.print(f"Updated group: {name}")

            # Create or retrieve permissions for the group from the fields within the data
            permissions = []

            # Permission to access project
            access_project_codename = f"access_{self.project.code}"
            access_project_permission, access_project_created = (
                Permission.objects.get_or_create(
                    content_type=self.project.content_type,
                    codename=access_project_codename,
                    defaults={
                        "name": f"Can access {self.project.code}",
                    },
                )
            )
            if access_project_created:
                self.print("Created permission:", access_project_permission)
            permissions.append(access_project_permission)

            group_actions = [Actions.ACCESS.label]
            for permission_config in group_config.permissions:
                if isinstance(permission_config.action, str):
                    actions = [permission_config.action]
                else:
                    actions = permission_config.action

                group_actions.extend(actions)

                for action in actions:
                    # Permission to action on project
                    action_project_codename = f"{action}_{self.project.code}"
                    action_project_permission, action_project_created = (
                        Permission.objects.get_or_create(
                            content_type=self.project.content_type,
                            codename=action_project_codename,
                            defaults={
                                "name": f"Can {action} {self.project.code}",
                            },
                        )
                    )
                    if action_project_created:
                        self.print("Created permission:", action_project_permission)
                    permissions.append(action_project_permission)

                    # Field permissions for the action
                    for field in permission_config.fields:
                        assert field, "Field cannot be empty."

                        # Permission to access field
                        access_field_codename = f"access_{self.project.code}__{field}"
                        access_field_permission, access_field_created = (
                            Permission.objects.get_or_create(
                                content_type=self.project.content_type,
                                codename=access_field_codename,
                                defaults={
                                    "name": f"Can access {self.project.code} {field}",
                                },
                            )
                        )
                        if access_field_created:
                            self.print("Created permission:", access_field_permission)
                        permissions.append(access_field_permission)

                        # Permission to action on field
                        action_field_codename = f"{action}_{self.project.code}__{field}"
                        action_field_permission, action_field_created = (
                            Permission.objects.get_or_create(
                                content_type=self.project.content_type,
                                codename=action_field_codename,
                                defaults={
                                    "name": f"Can {action} {self.project.code} {field}",
                                },
                            )
                        )
                        if action_field_created:
                            self.print("Created permission:", action_field_permission)
                        permissions.append(action_field_permission)

            # Set permissions for the group
            group.permissions.set(permissions)

            # Print permissions for the group
            if permissions:
                self.print(f"Permissions for {name}:")
                for perm in group.permissions.all():
                    self.print(f"• {perm}")
            else:
                self.print(f"Group {name} has no permissions.")

            # Add the group to the groups structure
            groups[group_config.scope] = (group, group_actions)

        # Create/update the corresponding projectgroup for each group
        for scope, (group, group_actions) in groups.items():
            projectgroup, pg_created = ProjectGroup.objects.update_or_create(
                group=group,
                defaults={
                    "project": self.project,
                    "scope": scope,
                    "actions": ",".join(group_actions),
                },
            )
            if pg_created:
                self.print(
                    f"Created project group: {projectgroup.project.code} | {projectgroup.scope}"
                )
            else:
                self.print(
                    f"Updated project group: {projectgroup.project.code} | {projectgroup.scope}"
                )
            self.print(f"• Actions: {' | '.join(group_actions)}")

    def set_choices(self, choice_configs: List[ChoiceConfig]):
        """
        Create/update the choices for the project.
        """

        for choice_config in choice_configs:
            # Create new choices if required
            for option in choice_config.options:
                if isinstance(option, ChoiceInfoConfig):
                    choice = option.choice
                    description = option.description
                else:
                    choice = option
                    description = ""

                try:
                    instance = Choice.objects.get(
                        project_id=self.project.code,
                        field=choice_config.field,
                        choice__iexact=choice,
                    )

                    if not instance.is_active:
                        # The choice was previously deactivated
                        instance.is_active = True
                        instance.save()
                        self.print(
                            f"Reactivated choice: {self.project.code} | {instance.field} | {instance.choice}",
                        )
                    else:
                        self.print(
                            f"Active choice: {self.project.code} | {instance.field} | {instance.choice}",
                        )

                    if instance.choice != choice:
                        # The case of the choice has changed
                        # e.g. lowercase -> uppercase
                        old = instance.choice
                        instance.choice = choice
                        instance.save()
                        self.print(
                            f"Renamed choice: {self.project.code} | {instance.field} | {old} -> {instance.choice}"
                        )

                    if instance.description != description:
                        instance.description = description
                        instance.save()
                        self.print(
                            f"Changed choice description: {self.project.code} | {instance.field} | {instance.choice}",
                        )

                except Choice.DoesNotExist:
                    instance = Choice.objects.create(
                        project_id=self.project.code,
                        field=choice_config.field,
                        choice=choice,
                        description=description,
                    )
                    self.print(
                        f"Created choice: {self.project.code} | {instance.field} | {instance.choice}",
                    )

            # Deactivate choices no longer in the set
            instances = Choice.objects.filter(
                project_id=self.project.code,
                field=choice_config.field,
                is_active=True,
            )

            active_choices = {
                option.choice if isinstance(option, ChoiceInfoConfig) else option
                for option in choice_config.options
            }

            for instance in instances:
                if instance.choice not in active_choices:
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

        # Empty constraints for the project
        for choice in Choice.objects.filter(project_id=self.project.code):
            choice.constraints.clear()

        for choice_constraint_config in choice_constraint_configs:
            choice_instance = Choice.objects.get(
                project_id=self.project.code,
                field=choice_constraint_config.field,
                choice__iexact=choice_constraint_config.option,
            )

            for constraint in choice_constraint_config.constraints:
                # Get each constraint choice instance
                constraint_instances = [
                    Choice.objects.get(
                        project_id=self.project.code,
                        field=constraint.field,
                        choice__iexact=constraint_option,
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
