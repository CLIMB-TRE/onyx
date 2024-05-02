from data.tests.utils import OnyxTestCase
from rest_framework.reverse import reverse


class TestActivityView(OnyxTestCase):
    def setUp(self):
        super().setUp()
        self.endpoint = reverse("accounts.activity")

    def test_basic(self):
        """
        Test retrieval of user activity.
        """

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])

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

        # Calls to other endpoints will also be recorded
        testproject_endpoint = reverse(
            "projects.testproject", kwargs={"code": self.project.code}
        )
        response = self.client.get(testproject_endpoint)
        status_code = response.status_code

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
