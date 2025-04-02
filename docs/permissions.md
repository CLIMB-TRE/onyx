# Permissions

## Roles

### Available roles

#### `is_active`

Active users are any user with access to Onyx.

Users with the `is_active` role (and no other roles) do not have access to any endpoints. Their account is 'waiting' to be approved. It can be viewed and approved by a member of staff from the `accounts.waiting` and `accounts.approve` endpoints respectively.

Account approval is currently managed by staff members only. In future, this could be managed by adding a 'site admin' role to Onyx (if it became a requested feature).

To de-activate a user, and lock them out of Onyx, set their `is_active` role to `False`.

#### `is_approved`

Approved users represent the standard user in Onyx.

Users with the `is_active` and `is_approved` roles gain the ability to:

- Login/logout via the `knox_login`, `knox_logout` and `knox_logoutall` endpoints
- View their profile via the `accounts.profile` endpoint
- List their latest API activity via the `accounts.activity` endpoint
- List other users in their site via the `accounts.siteusers` endpoint
- List their available projects via the `projects` endpoint
- List information about project data types via the `projects.types` endpoint
- List information about type lookups via the `projects.lookups` endpoint

To interact with data from a specific project, they would need to be assigned to a **group**. The type of group(s) they are a member of determines what **actions** they can carry out in a project.

#### `is_staff`

Staff users are special users with elevated privileges in Onyx.

Users with the `is_active`, `is_approved` and `is_staff` roles gain the ability to:

- List users waiting for approval via the `accounts.waiting` endpoint
- Approve waiting users via the `accounts.approve` endpoint
- List users across all sites via the `accounts.allusers` endpoint
- Create/retrieve a user in a specific site, with permission to view a specific project, via the `accounts.projectuser` endpoint
- For a given project they are assigned to:
  - View value changes in the history of an object for any site
  - Recover an anonymised identifier for any site
  - Update an object for any site
  - Delete an object for any site

### Managing roles for a user

#### List roles for a user

```
$ python manage.py user roles <USER>
```

#### Grant roles to a user

```
$ python manage.py user roles <USER> --grant <ROLE1> <ROLE2>
```

#### Revoke roles from a user

```
$ python manage.py user roles <USER> --revoke <ROLE1> <ROLE2>
```

## Groups

### Available groups

#### `admin`

#### `uploader`

#### `analyst`

### Managing groups for a user

#### List groups for a user

```
$ python manage.py user groups <USER>
```

#### Grant groups to a user

```
$ python manage.py user groups <USER> --grant <GROUP1> <GROUP2> ...
```

Match multiple group names via a regular expression:

```
$ python manage.py user groups <USER> --rxgrant <REGEX>
```

#### Revoke groups from a user

```
$ python manage.py user groups <USER> --revoke <GROUP1> <GROUP2> ...
```

Match multiple group names via a regular expression:

```
$ python manage.py user groups <USER> --rxrevoke <REGEX>
```
