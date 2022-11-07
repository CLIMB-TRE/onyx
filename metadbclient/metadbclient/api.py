import os
import sys
import csv
import json
import requests
from metadbclient import utils, settings
from metadbclient.field import Field
from metadbclient.config import Config


class Client:
    def __init__(self, config):
        """
        Initialise the client with a given config.
        """
        self.config = config
        self.url = f"http://{self.config.host}:{self.config.port}"
        self.endpoints = {
            # accounts
            "register": f"{self.url}/accounts/register/",
            "login": f"{self.url}/accounts/login/",
            "logout": f"{self.url}/accounts/logout/",
            "logoutall": f"{self.url}/accounts/logoutall/",
            "site_approve": lambda x: f"{self.url}/accounts/site/approve/{x}/",
            "site_waiting": f"{self.url}/accounts/site/waiting/",
            "site_users": f"{self.url}/accounts/site/users/",
            "admin_approve": lambda x: f"{self.url}/accounts/admin/approve/{x}/",
            "admin_waiting": f"{self.url}/accounts/admin/waiting/",
            "admin_users": f"{self.url}/accounts/admin/users/",
            # data
            "pathogens": f"{self.url}/data/pathogens/",
            "query": lambda x: f"{self.url}/data/{x}/query/",
            "create": lambda x: f"{self.url}/data/{x}/",
            "get": lambda x: f"{self.url}/data/{x}/",
            "update": lambda x, y: f"{self.url}/data/{x}/{y}/",
            "suppress": lambda x, y: f"{self.url}/data/{x}/{y}",
        }

    def request(self, method, **kwargs):
        kwargs.setdefault("headers", {}).update(
            {"Authorization": f"Token {self.token}"}
        )
        method_response = method(**kwargs)
        if method_response.status_code == 401:
            password = self.get_password()
            login_response = requests.post(
                self.endpoints["login"],
                auth=(self.username, password),
            )
            if login_response.ok:
                self.token = login_response.json().get("token")
                self.expiry = login_response.json().get("expiry")
                self.config.write_token(self.username, self.token, self.expiry)

                kwargs.setdefault("headers", {}).update(
                    {"Authorization": f"Token {self.token}"}
                )
                method_response = method(**kwargs)

            else:
                return login_response

        return method_response

    def register(self, first_name, last_name, email, site, password):
        """
        Create a new user.
        """
        response = requests.post(
            self.endpoints["register"],
            json={
                "first_name": first_name,
                "last_name": last_name,
                "password": password,
                "email": email,
                "site": site,
            },
        )
        return response

    def continue_session(self, username=None, env_password=False):
        if username is None:
            # Attempt to use default_user if no username was provided
            if self.config.default_user is None:
                raise Exception(
                    "No username was provided and there is no default_user in the config. Either provide a username or set a default_user"
                )
            else:
                # The default_user must be in the config
                if self.config.default_user not in self.config.users:
                    raise Exception(
                        f"default_user '{self.config.default_user}' is not in the users list for the config"
                    )
                username = self.config.default_user
        else:
            # Username is case-insensitive
            username = username.lower()

            # The provided user must be in the config
            if username not in self.config.users:
                raise KeyError(
                    f"User '{username}' is not in the config. Add them using the add-user config command"
                )

        # Assign username to the client
        self.username = username

        # Assign flag indicating whether to look for user's password to the client
        self.env_password = env_password

        # Open the token file for the user and assign the current token, and its expiry, to the client
        with open(self.config.users[username]["token"]) as token_file:
            token_data = json.load(token_file)
            self.token = token_data.get("token")
            self.expiry = token_data.get("expiry")

        return username

    def get_password(self):
        if self.env_password:
            # If the password is meant to be an env var, grab it. If its not there, this is unintended so raise an error
            password_env_var = (
                settings.PASSWORD_ENV_VAR_PREFIX
                + self.username.upper()
                + settings.PASSWORD_ENV_VAR_POSTFIX
            )
            password = os.getenv(password_env_var)
            if password is None:
                raise KeyError(f"Environment variable '{password_env_var}' is not set")
        else:
            # Otherwise, prompt for the password
            print("Please enter your password.")
            password = utils.get_input("password", password=True)
        return password

    def login(self, username=None, env_password=False):
        """
        Log in as a particular user, get a new token and store the token in the client.

        If no user is provided, the `default_user` in the config is used.
        """

        # Assigns username/env_password flag to the client
        self.continue_session(username, env_password=env_password)

        # Get the password
        password = self.get_password()

        # Log in
        response = requests.post(
            self.endpoints["login"], auth=(self.username, password)
        )
        if response.ok:
            self.token = response.json().get("token")
            self.expiry = response.json().get("expiry")
            self.config.write_token(self.username, self.token, self.expiry)

        return response

    @utils.session_required
    def logout(self):
        """
        Log out the user.
        """
        response = self.request(
            method=requests.post,
            url=self.endpoints["logout"],
        )
        if response.ok:
            self.token = None
            self.expiry = None
            self.config.write_token(self.username, self.token, self.expiry)

        return response

    @utils.session_required
    def logoutall(self):
        """
        Log out the user everywhere.
        """
        response = self.request(
            method=requests.post,
            url=self.endpoints["logoutall"],
        )
        if response.ok:
            self.token = None
            self.expiry = None
            self.config.write_token(self.username, self.token, self.expiry)

        return response

    @utils.session_required
    def site_approve(self, username):
        """
        Site-approve another user.
        """
        response = self.request(
            method=requests.patch,
            url=self.endpoints["site_approve"](username),
        )
        return response

    @utils.session_required
    def site_list_waiting(self):
        """
        List users waiting for site approval.
        """
        response = self.request(
            method=requests.get,
            url=self.endpoints["site_waiting"],
        )
        return response

    @utils.session_required
    def site_list_users(self):
        """
        Get the current users within the site of the requesting user.
        """
        response = self.request(
            method=requests.get,
            url=self.endpoints["site_users"],
        )
        return response

    @utils.session_required
    def admin_approve(self, username):
        """
        Admin-approve another user.
        """
        response = self.request(
            method=requests.patch,
            url=self.endpoints["admin_approve"](username),
        )
        return response

    @utils.session_required
    def admin_list_waiting(self):
        """
        List users waiting for admin approval.
        """
        response = self.request(
            method=requests.get,
            url=self.endpoints["admin_waiting"],
        )
        return response

    @utils.session_required
    def admin_list_users(self):
        """
        List all users.
        """
        response = self.request(
            method=requests.get,
            url=self.endpoints["admin_users"],
        )
        return response

    @utils.session_required
    def list_pathogen_codes(self):
        """
        List the current pathogens within the database.
        """
        response = self.request(
            method=requests.get,
            url=self.endpoints["pathogens"],
        )
        return response

    @utils.session_required
    def create(self, pathogen_code, fields):
        """
        Post a pathogen record to the database.
        """
        response = self.request(
            method=requests.post,
            url=self.endpoints["create"](pathogen_code),
            json=fields,
        )
        return response

    @utils.session_required
    def csv_create(self, pathogen_code, csv_path, delimiter=None):
        """
        Post a .csv or .tsv containing pathogen records to the database.
        """
        if csv_path == "-":
            csv_file = sys.stdin
        else:
            csv_file = open(csv_path)
        try:
            if delimiter is None:
                reader = csv.DictReader(csv_file)
            else:
                reader = csv.DictReader(csv_file, delimiter=delimiter)

            for record in reader:
                response = self.request(
                    method=requests.post,
                    url=self.endpoints["create"](pathogen_code),
                    json=record,
                )
                yield response
        finally:
            if csv_file is not sys.stdin:
                csv_file.close()

    @utils.session_required
    def get(self, pathogen_code, cid=None, fields=None, **kwargs):
        """
        Get records from the database.
        """
        if fields is None:
            fields = {}

        if cid is not None:
            fields.setdefault("cid", []).append(cid)

        for field, values in kwargs.items():
            if isinstance(values, list):
                for v in values:
                    if isinstance(v, tuple):
                        v = ",".join(str(x) for x in v)

                    fields.setdefault(field, []).append(v)
            else:
                if isinstance(values, tuple):
                    values = ",".join(str(x) for x in values)

                fields.setdefault(field, []).append(values)

        response = self.request(
            method=requests.get,
            url=self.endpoints["get"](pathogen_code),
            params=fields,
        )
        yield response

        if response.ok:
            _next = response.json()["next"]
        else:
            _next = None

        while _next is not None:
            response = self.request(
                method=requests.get,
                url=_next,
            )
            yield response

            if response.ok:
                _next = response.json()["next"]
            else:
                _next = None

    @utils.session_required
    def query(self, pathogen_code, query):
        """
        Get records from the database.
        """
        if not isinstance(query, Field):
            raise Exception("Query must be of type Field")

        response = self.request(
            method=requests.post,
            url=self.endpoints["query"](pathogen_code),
            json=query.query,
        )

        return response

    @utils.session_required
    def update(self, pathogen_code, cid, fields):
        """
        Update a pathogen record in the database.
        """
        response = self.request(
            method=requests.patch,
            url=self.endpoints["update"](pathogen_code, cid),
            json=fields,
        )
        return response

    @utils.session_required
    def csv_update(self, pathogen_code, csv_path, delimiter=None):
        """
        Use a .csv or .tsv to update pathogen records in the database.
        """
        if csv_path == "-":
            csv_file = sys.stdin
        else:
            csv_file = open(csv_path)
        try:
            if delimiter is None:
                reader = csv.DictReader(csv_file)
            else:
                reader = csv.DictReader(csv_file, delimiter=delimiter)

            for record in reader:
                cid = record.pop("cid", None)
                if cid is None:
                    raise KeyError("cid column must be provided")

                response = self.request(
                    method=requests.patch,
                    url=self.endpoints["update"](pathogen_code, cid),
                    json=record,
                )
                yield response
        finally:
            if csv_file is not sys.stdin:
                csv_file.close()

    @utils.session_required
    def suppress(self, pathogen_code, cid):
        """
        Suppress a pathogen record in the database.
        """
        response = self.request(
            method=requests.delete,
            url=self.endpoints["suppress"](pathogen_code, cid),
        )
        return response

    @utils.session_required
    def csv_suppress(self, pathogen_code, csv_path, delimiter=None):
        """
        Use a .csv or .tsv to suppress pathogen records in the database.
        """
        if csv_path == "-":
            csv_file = sys.stdin
        else:
            csv_file = open(csv_path)
        try:
            if delimiter is None:
                reader = csv.DictReader(csv_file)
            else:
                reader = csv.DictReader(csv_file, delimiter=delimiter)

            for record in reader:
                cid = record.get("cid")
                if cid is None:
                    raise KeyError("cid column must be provided")

                response = self.request(
                    method=requests.delete,
                    url=self.endpoints["suppress"](pathogen_code, cid),
                )
                yield response
        finally:
            if csv_file is not sys.stdin:
                csv_file.close()


class Session:
    def __init__(self, username=None, env_password=False, login=False, logout=False):
        self.config = Config()
        self.client = Client(self.config)
        self.username = username
        self.env_password = env_password
        self.login = login
        self.logout = logout

    def __enter__(self):
        if self.login:
            response = self.client.login(
                username=self.username,
                env_password=self.env_password,
            )
            response.raise_for_status()
        else:
            self.client.continue_session(
                username=self.username,
                env_password=self.env_password,
            )
        return self.client

    def __exit__(self, type, value, traceback):
        if self.logout:
            self.client.logout()