import json
from typing import Optional, List, Dict
from pydantic import BaseModel, field_validator
from django.core.management import base
from django.db import transaction
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from ...models import Project, ProjectGroup, Choice
from ...types import Actions, Scopes, Objects


OBJECT_TYPE_LABELS = [obj.label for obj in Objects]
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
    object_type: str = Objects.RECORD.label
    permissions: List[PermissionConfig]

    @field_validator("object_type")
    def validate_object_type(cls, value):
        assert value in OBJECT_TYPE_LABELS, f"Invalid object type: {value}"
        return value


class ChoiceInfoConfig(BaseModel):
    choice: str
    description: str


class ChoiceConfig(BaseModel):
    field: str
    options: List[str | ChoiceInfoConfig]
    override: bool = False


class ChoiceConstraintConfig(BaseModel):
    field: str
    option: str
    constraints: List[ChoiceConfig]


class ProjectConfig(BaseModel):
    code: str
    name: Optional[str]
    description: Optional[str]
    content_type: str


class ProjectContentsConfig(BaseModel):
    code: str | List[str]
    groups: Optional[List[GroupConfig]]
    choices: Optional[List[ChoiceConfig]]
    choice_constraints: Optional[List[ChoiceConstraintConfig]]


class Config(BaseModel):
    projects: List[ProjectConfig]
    contents: Optional[List[ProjectContentsConfig]]


def get_analysis_groups(project: str) -> List[GroupConfig]:
    """
    Get the analysis groups for the provided `project`.
    """

    return [
        GroupConfig(
            **{
                "scope": Scopes.ADMIN.label,
                "object_type": Objects.ANALYSIS.label,
                "permissions": [
                    {
                        "action": ["add", "testadd"],
                        "fields": ["site"],
                    },
                    {
                        "action": ["history", "change", "testchange"],
                        "fields": ["is_suppressed"],
                    },
                    {
                        "action": ["add", "testadd", "change", "testchange"],
                        "fields": [
                            "is_published",
                            "analysis_date",
                            "name",
                            "description",
                            "pipeline_name",
                            "pipeline_url",
                            "pipeline_version",
                            "pipeline_command",
                            "methods",
                            "result",
                            "result_metrics",
                            "report",
                            "outputs",
                            "upstream_analyses",
                            "identifiers",
                            f"{project}_records",
                        ],
                    },
                    {
                        "action": ["get", "list", "filter", "history"],
                        "fields": [
                            "is_published",
                            "published_date",
                            "site",
                            "analysis_id",
                            "analysis_date",
                            "name",
                            "report",
                            "outputs",
                        ],
                    },
                    {
                        "action": ["get", "filter", "history"],
                        "fields": [
                            "description",
                            "pipeline_name",
                            "pipeline_url",
                            "pipeline_version",
                            "pipeline_command",
                            "methods",
                            "result",
                            "result_metrics",
                        ],
                    },
                    {
                        "action": ["get", "filter"],
                        "fields": [
                            "upstream_analyses",
                            "downstream_analyses",
                            "identifiers",
                            f"{project}_records",
                        ],
                    },
                    {
                        "action": "filter",
                        "fields": [
                            "upstream_analyses__analysis_id",
                            "downstream_analyses__analysis_id",
                            f"{project}_records__climb_id",
                        ],
                    },
                ],
            }
        ),
        GroupConfig(
            **{
                "scope": Scopes.UPLOADER.label,
                "object_type": Objects.ANALYSIS.label,
                "permissions": [
                    {
                        "action": ["add", "testadd"],
                        "fields": ["is_published", "site"],
                    },
                    {
                        "action": ["add", "testadd", "change", "testchange"],
                        "fields": [
                            "analysis_date",
                            "name",
                            "description",
                            "pipeline_name",
                            "pipeline_url",
                            "pipeline_version",
                            "pipeline_command",
                            "methods",
                            "result",
                            "result_metrics",
                            "report",
                            "outputs",
                            "upstream_analyses",
                            "identifiers",
                            f"{project}_records",
                        ],
                    },
                ],
            }
        ),
        GroupConfig(
            **{
                "scope": Scopes.ANALYSIS_UPLOADER.label,
                "object_type": Objects.ANALYSIS.label,
                "permissions": [
                    {
                        "action": ["add", "testadd", "change", "testchange"],
                        "fields": [
                            "is_published",
                            "analysis_date",
                            "name",
                            "description",
                            "pipeline_name",
                            "pipeline_url",
                            "pipeline_version",
                            "pipeline_command",
                            "methods",
                            "result",
                            "result_metrics",
                            "report",
                            "outputs",
                            "upstream_analyses",
                            "identifiers",
                            f"{project}_records",
                        ],
                    },
                ],
            }
        ),
        GroupConfig(
            **{
                "scope": Scopes.ANALYST.label,
                "object_type": Objects.ANALYSIS.label,
                "permissions": [
                    {
                        "action": ["get", "list", "filter", "history"],
                        "fields": [
                            "published_date",
                            "site",
                            "analysis_id",
                            "analysis_date",
                            "name",
                            "report",
                            "outputs",
                        ],
                    },
                    {
                        "action": ["get", "filter", "history"],
                        "fields": [
                            "description",
                            "pipeline_name",
                            "pipeline_url",
                            "pipeline_version",
                            "pipeline_command",
                            "methods",
                            "result",
                            "result_metrics",
                        ],
                    },
                    {
                        "action": ["get", "filter"],
                        "fields": [
                            "upstream_analyses",
                            "downstream_analyses",
                            "identifiers",
                            f"{project}_records",
                        ],
                    },
                    {
                        "action": "filter",
                        "fields": [
                            "upstream_analyses__analysis_id",
                            "downstream_analyses__analysis_id",
                            f"{project}_records__climb_id",
                        ],
                    },
                ],
            }
        ),
    ]


class Command(base.BaseCommand):
    help = "Create/manage projects."

    def add_arguments(self, parser):
        parser.add_argument("config")
        parser.add_argument("--quiet", action="store_true")

    def print(self, *args, **kwargs):
        if not self.quiet:
            print(*args, **kwargs)

    def handle(self, *args, **options):
        self.quiet = options["quiet"]

        with open(options["config"]) as config_file:
            config = Config.model_validate(json.load(config_file))

        with transaction.atomic():
            for project_config in config.projects:
                self.set_project(project_config, config.contents)

    def set_project(
        self,
        project_config: ProjectConfig,
        contents: Optional[List[ProjectContentsConfig]],
    ):
        """
        Create/update the project.
        """

        # Get the app and model from the content type
        app, _, model = project_config.content_type.partition(".")

        if model != project_config.code:
            raise ValueError(
                f"Model name '{model}' does not match project code '{project_config.code}'."
            )

        # Create or retrieve the project
        project, p_created = Project.objects.update_or_create(
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
            self.print(f"Creating project: {project.code}")
        else:
            self.print(f"Updating project: {project.code}")

        if contents:
            # Mapping of scope to object type to permissions
            groups = {}

            # Mapping of field to choice configurations
            choice_configs = {}

            # List of choice constraints
            choice_constraints = []

            # Iterate through the contents to gather groups, choices, and choice constraints
            for content in contents:
                if (
                    isinstance(content.code, list)
                    and project_config.code in content.code
                ) or (
                    isinstance(content.code, str)
                    and project_config.code == content.code
                ):
                    if content.groups:
                        # Create a list of permissions for a given scope and object type
                        # or extend if it already exists
                        for group in content.groups:
                            groups.setdefault(group.scope, {}).setdefault(
                                group.object_type, []
                            ).extend(group.permissions)

                    if content.choices:
                        for choice_config in content.choices:
                            if choice_config.override:
                                choice_configs[choice_config.field] = [choice_config]
                            else:
                                choice_configs.setdefault(
                                    choice_config.field, []
                                ).append(choice_config)

                    if content.choice_constraints:
                        choice_constraints.extend(content.choice_constraints)

            # Add analysis permissions for the project scopes
            for group in get_analysis_groups(project.code):
                groups.setdefault(group.scope, {}).setdefault(
                    group.object_type, []
                ).extend(group.permissions)

            # Set the groups, choices, and choice constraints for the project
            if groups:
                # Convert from scope/object/permissions mapping
                # to mapping of scope to list of group configs (one for each object type)
                group_configs = {}
                for scope, object_types in groups.items():
                    for object_type, permissions in object_types.items():
                        group_configs.setdefault(scope, []).append(
                            GroupConfig(
                                scope=scope,
                                object_type=object_type,
                                permissions=permissions,
                            )
                        )

                self.set_groups(project=project, group_configs=group_configs)

            if choice_configs:
                # Convert field/ChoiceConfig mapping to list of ChoiceConfig objects
                choices = [
                    choice_config
                    for choice_config_list in choice_configs.values()
                    for choice_config in choice_config_list
                ]
                self.set_choices(project, choices)

            if choice_constraints:
                self.set_choice_constraints(project, choice_constraints)

        if p_created:
            self.print(f"Created project: {project.code}")
        else:
            self.print(f"Updated project: {project.code}")

        self.print("• Name:", project.name)
        self.print("• Description:", project.description)
        self.print("• Model:", project.content_type.model_class())

    def create_update_permission(
        self,
        content_type: ContentType,
        action: str,
        project: Project,
        object_type: Optional[str] = None,
        field: Optional[str] = None,
    ):
        """
        Create or update a permission.
        """

        codename = f"{action}_{project.code}"
        name = f"Can {action} {project.code}"

        if field and not object_type:
            raise ValueError("Object type is required if field is provided.")

        if object_type:
            codename += f"_{object_type}"
            name += f" {object_type}"

        if field:
            codename += f"__{field}"
            name += f" {field}"

        permission, created = Permission.objects.update_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )

        if created:
            self.print("Created permission:", permission)

        return permission

    def set_groups(self, project: Project, group_configs: Dict[str, List[GroupConfig]]):
        """
        Create/update the groups for the project.
        """

        # TODO: How should ContentType be handled for different objects in permissions?

        groups = {}

        # For each scope, combine configs into a group
        for scope, configs in group_configs.items():
            # Create or retrieve underlying permissions group
            # This is based on project code and scope
            name = f"{project.code}.{scope}"
            group, g_created = Group.objects.get_or_create(name=name)

            if g_created:
                self.print(f"Created group: {name}")
            else:
                self.print(f"Updated group: {name}")

            # Group actions
            group_actions = {Actions.ACCESS.label}

            # Group permissions
            permissions = {}

            # Create/update permission to access project
            access = (Actions.ACCESS.label,)
            if access not in permissions:
                permissions[access] = self.create_update_permission(
                    content_type=project.content_type,
                    action=Actions.ACCESS.label,
                    project=project,
                )

            # Create/update permissions for each object type
            for config in configs:
                # Create/update permission to access the object type
                access_object_type = (Actions.ACCESS.label, config.object_type)
                if access_object_type not in permissions:
                    permissions[access_object_type] = self.create_update_permission(
                        content_type=project.content_type,
                        action=Actions.ACCESS.label,
                        project=project,
                        object_type=config.object_type,
                    )

                # Create/update action permissions for the object type
                for permission_config in config.permissions:
                    # Get list of actions in the permission config
                    if isinstance(permission_config.action, str):
                        actions = [permission_config.action]
                    else:
                        actions = permission_config.action

                    # Add actions to the list of actions for the group
                    group_actions.update(actions)

                    for action in actions:
                        # Create/update permission to action on the object type
                        action_object_type = (action, config.object_type)
                        if action_object_type not in permissions:
                            permissions[action_object_type] = (
                                self.create_update_permission(
                                    content_type=project.content_type,
                                    action=action,
                                    project=project,
                                    object_type=config.object_type,
                                )
                            )

                        # Field permissions for the action
                        for field in permission_config.fields:
                            assert field, "Field cannot be empty."

                            # Create/update permission to access the object's field
                            access_object_field = (
                                Actions.ACCESS.label,
                                config.object_type,
                                field,
                            )
                            if access_object_field not in permissions:
                                permissions[access_object_field] = (
                                    self.create_update_permission(
                                        content_type=project.content_type,
                                        action=Actions.ACCESS.label,
                                        project=project,
                                        object_type=config.object_type,
                                        field=field,
                                    )
                                )

                            # Create/update permission to action on the object's field
                            action_object_field = (action, config.object_type, field)
                            if action_object_field not in permissions:
                                permissions[action_object_field] = (
                                    self.create_update_permission(
                                        content_type=project.content_type,
                                        action=action,
                                        project=project,
                                        object_type=config.object_type,
                                        field=field,
                                    )
                                )

            # Set permissions for the group
            group.permissions.set(permissions.values())

            # Print permissions for the group
            if permissions:
                self.print(f"Permissions for {name}:")
                for perm in group.permissions.all():
                    self.print(f"• {perm}")
            else:
                self.print(f"Group {name} has no permissions.")

            # Add the group to the groups structure
            groups[scope] = (group, group_actions)

        # Create/update the corresponding projectgroup for each group
        for scope, (group, group_actions) in groups.items():
            actions = [action for action in ACTION_LABELS if action in group_actions]
            projectgroup, pg_created = ProjectGroup.objects.update_or_create(
                group=group,
                defaults={
                    "project": project,
                    "scope": scope,
                    "actions": ",".join(actions),
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
            self.print(f"• Actions: {' | '.join(actions)}")

    def set_choices(self, project: Project, choice_configs: List[ChoiceConfig]):
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
                        project=project,
                        field=choice_config.field,
                        choice__iexact=choice,
                    )

                    if not instance.is_active:
                        # The choice was previously deactivated
                        instance.is_active = True
                        instance.save()
                        self.print(
                            f"Reactivated choice: {project.code} | {instance.field} | {instance.choice}",
                        )
                    else:
                        # self.print(
                        #     f"Active choice: {project.code} | {instance.field} | {instance.choice}",
                        # )
                        pass

                    if instance.choice != choice:
                        # The case of the choice has changed
                        # e.g. lowercase -> uppercase
                        old = instance.choice
                        instance.choice = choice
                        instance.save()
                        self.print(
                            f"Renamed choice: {project.code} | {instance.field} | {old} -> {instance.choice}"
                        )

                    if instance.description != description:
                        instance.description = description
                        instance.save()
                        self.print(
                            f"Changed choice description: {project.code} | {instance.field} | {instance.choice}",
                        )

                except Choice.DoesNotExist:
                    instance = Choice.objects.create(
                        project=project,
                        field=choice_config.field,
                        choice=choice,
                        description=description,
                    )
                    self.print(
                        f"Created choice: {project.code} | {instance.field} | {instance.choice}",
                    )

            # Deactivate choices no longer in the set
            instances = Choice.objects.filter(
                project=project,
                field=choice_config.field,
                is_active=True,
            )

            # TODO: Fix active choices to account for all contents
            active_choices = {
                option.choice if isinstance(option, ChoiceInfoConfig) else option
                for option in choice_config.options
            }

            for instance in instances:
                if instance.choice not in active_choices:
                    instance.is_active = False
                    instance.save()
                    self.print(
                        f"Deactivated choice: {project.code} | {instance.field} | {instance.choice}",
                    )

    def set_choice_constraints(
        self, project: Project, choice_constraint_configs: List[ChoiceConstraintConfig]
    ):
        """
        Create/update the choice constraints for the project.
        """

        # Empty constraints for the project
        for choice in Choice.objects.filter(project=project):
            choice.constraints.clear()

        for choice_constraint_config in choice_constraint_configs:
            choice_instance = Choice.objects.get(
                project=project,
                field=choice_constraint_config.field,
                choice__iexact=choice_constraint_config.option,
            )

            for constraint in choice_constraint_config.constraints:
                # Get each constraint choice instance
                constraint_instances = [
                    Choice.objects.get(
                        project=project,
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
                        f"Set constraint: {project.code} | ({choice_instance.field}, {choice_instance.choice}) | ({constraint_instance.field}, {constraint_instance.choice})",
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
