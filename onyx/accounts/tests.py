from rest_framework.reverse import reverse
from data.tests.utils import OnyxTestCase
from .models import User
from internal.models import RequestHistory


class TestProfileView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the analyst user
        self.client.force_authenticate(self.analyst_user)  # type: ignore
        self.endpoint = reverse("accounts.profile")

    def test_basic(self):
        """
        Test retrieval of the user's profile.
        """

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["data"]["username"], self.analyst_user.username
        )
        self.assertEqual(response.json()["data"]["site"], self.analyst_user.site.code)
        self.assertEqual(response.json()["data"]["email"], self.analyst_user.email)


class TestActivityView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the analyst user
        self.client.force_authenticate(self.analyst_user)  # type: ignore
        self.endpoint = reverse("accounts.activity")

    def test_basic(self):
        """
        Test retrieval of user activity.
        """

        self.assertEqual(RequestHistory.objects.count(), 0)

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])
        self.assertEqual(RequestHistory.objects.count(), 1)

        # Making the request again will show the previous call to the activity endpoint
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 1)
        self.assertEqual(
            response.json()["data"][0]["endpoint"], reverse("accounts.activity")
        )
        self.assertEqual(response.json()["data"][0]["method"], "GET")
        self.assertEqual(response.json()["data"][0]["status"], 200)
        self.assertEqual(response.json()["data"][0]["error_messages"], "")
        self.assertEqual(RequestHistory.objects.count(), 2)

        # Calls to other endpoints will also be recorded
        testproject_endpoint = reverse(
            "projects.testproject", kwargs={"code": self.project.code}
        )
        response = self.client.get(testproject_endpoint)
        status_code = response.status_code
        self.assertEqual(RequestHistory.objects.count(), 3)

        # Making the activity request again will show the previous call to the testproject endpoint,
        # as well as the previous calls to the activity endpoint
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 3)
        for i in [0, 1]:
            self.assertEqual(
                response.json()["data"][i]["endpoint"], reverse("accounts.activity")
            )
            self.assertEqual(response.json()["data"][i]["method"], "GET")
            self.assertEqual(response.json()["data"][i]["status"], 200)
            self.assertEqual(response.json()["data"][i]["error_messages"], "")
        self.assertEqual(response.json()["data"][2]["endpoint"], testproject_endpoint)
        self.assertEqual(response.json()["data"][0]["method"], "GET")
        self.assertEqual(response.json()["data"][0]["status"], status_code)
        self.assertEqual(response.json()["data"][0]["error_messages"], "")
        self.assertEqual(RequestHistory.objects.count(), 4)


class TestWaitingUsersView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the staff user
        self.client.force_authenticate(self.admin_staff)  # type: ignore
        self.endpoint = reverse("accounts.waiting")

    def test_basic(self):
        """
        Test retrieval of waiting users.
        """

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])

        # Create a waiting user (active but unapproved)
        self.create_user(username="waiting_user", site=self.site, roles=["is_active"])

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 1)
        self.assertEqual(response.json()["data"][0]["username"], "waiting_user")
        self.assertEqual(response.json()["data"][0]["site"], self.site.code)


class TestApproveUserView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the staff user
        self.client.force_authenticate(self.admin_staff)  # type: ignore
        self.waiting_user = self.create_user(
            username="waiting_user", site=self.site, roles=["is_active"]
        )
        self.endpoint = lambda username: reverse(
            "accounts.approve", kwargs={"username": username}
        )

    def test_basic(self):
        """
        Test approval of a waiting user.
        """

        self.assertFalse(self.waiting_user.is_approved)
        response = self.client.patch(self.endpoint(self.waiting_user.username))
        self.assertEqual(response.status_code, 200)
        self.waiting_user.refresh_from_db()
        self.assertTrue(self.waiting_user.is_approved)

    def test_user_not_found(self):
        """
        Test approval of a user that does not exist.
        """

        response = self.client.patch(self.endpoint("nonexistent_user"))
        self.assertEqual(response.status_code, 404)


class TestSiteUsersView(OnyxTestCase):
    def setUp(self):
        super().setUp()
        self.endpoint = reverse("accounts.siteusers")

    def test_basic(self):
        """
        Test retrieval of site users.
        """

        # Authenticate as the analyst user
        self.client.force_authenticate(self.analyst_user)  # type: ignore

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.json()["data"]), User.objects.filter(site=self.site).count()
        )
        self.assertTrue(
            all(user["site"] == self.site.code for user in response.json()["data"])
        )

    def test_basic_other_site(self):
        """
        Test retrieval of site users for a different site.
        """

        # Authenticate as the extra analyst user
        self.client.force_authenticate(self.analyst_user_extra)  # type: ignore

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.json()["data"]),
            User.objects.filter(site=self.extra_site).count(),
        )
        self.assertTrue(
            all(
                user["site"] == self.extra_site.code for user in response.json()["data"]
            )
        )


class TestAllUsersView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the staff user
        self.client.force_authenticate(self.admin_staff)  # type: ignore
        self.endpoint = reverse("accounts.allusers")

    def test_basic(self):
        """
        Test retrieval of all users.
        """

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), User.objects.count())


class TestProjectUserView(OnyxTestCase):
    # TODO: More tests

    def setUp(self):
        super().setUp()

        # Authenticate as the staff user
        self.client.force_authenticate(self.admin_staff)  # type: ignore
        self.endpoint = lambda project_code, site_code, username: reverse(
            "accounts.projectuser",
            kwargs={
                "project_code": project_code,
                "site_code": site_code,
                "username": username,
            },
        )

    def test_basic(self):
        """
        Test creation of a user with permission to view a specific project.
        """

        # Create a user with permission to view the project
        response = self.client.post(
            self.endpoint(self.project.code, self.site.code, "project_user"),
        )
        self.assertEqual(response.status_code, 200)
