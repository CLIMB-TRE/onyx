from typing import Optional, List, Tuple, Union
from django.contrib.auth.models import Group
from accounts.models import User, Site


def manage_instance_roles(
    instance: Union[User, Site],
    roles: List[str],
    granted: Optional[List[str]],
    revoked: Optional[List[str]],
) -> Tuple[List[str], List[str]]:
    """
    Grant or revoke roles to an instance.

    Args:
        instance: The instance.
        roles: A list of allowed roles to grant/revoke.
        granted: A list of roles to grant.
        revoked: A list of roles to revoke.

    Returns:
        A tuple containing lists of granted and revoked roles.
    """

    granted_roles = []
    revoked_roles = []

    if granted:
        for role in granted:
            if not hasattr(instance, role):
                raise Exception("Role is unknown")

            if role not in roles:
                raise Exception("Role cannot be changed")

            setattr(instance, role, True)
            granted_roles.append(role)

        instance.save(update_fields=granted_roles)

    if revoked:
        for role in revoked:
            if not hasattr(instance, role):
                raise Exception("Role is unknown")

            if role not in roles:
                raise Exception("Role cannot be changed")

            setattr(instance, role, False)
            revoked_roles.append(role)

        instance.save(update_fields=revoked_roles)

    return granted_roles, revoked_roles


def manage_instance_groups(
    instance: User,
    granted: Optional[List[str]],
    revoked: Optional[List[str]],
    grant_regex: Optional[str],
    revoke_regex: Optional[str],
) -> Tuple[List[str], List[str]]:
    """
    Grant or revoke groups to a user.

    Args:
        instance: The user instance.
        granted: A list of groups to grant.
        revoked: A list of groups to revoke.
        grant_regex: A regex to grant groups by.
        revoke_regex: A regex to revoke groups by.

    Returns:
        A tuple containing lists of granted and revoked groups.
    """

    granted_groups = []
    revoked_groups = []

    qs = Group.objects.all()

    if getattr(instance, "is_projectuser", False):
        qs = qs.filter(projectgroup__project=instance.project)

    if granted:
        for g in granted:
            group = qs.get(name=g)
            instance.groups.add(group)
            granted_groups.append(group.name)

    if grant_regex:
        for group in qs.filter(name__regex=grant_regex):
            instance.groups.add(group)
            granted_groups.append(group.name)

    if revoked:
        for g in revoked:
            group = qs.get(name=g)
            instance.groups.remove(group)
            revoked_groups.append(group.name)

    if revoke_regex:
        for group in qs.filter(name__regex=revoke_regex):
            instance.groups.remove(group)
            revoked_groups.append(group.name)

    return granted_groups, revoked_groups


def list_instances(instances) -> None:
    """
    Print a table of instances, with their attributes.

    Args:
        instances: A list of instances, each represented as a dictionary of attributes.
    """

    for instance_attrs in instances:
        print(*(f"{key}={val}" for key, val in instance_attrs.items()), sep="\t")
