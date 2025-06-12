from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase


class TestProjectsView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the analyst user
        self.client.force_authenticate(self.analyst_user)  # type: ignore

        self.endpoint = reverse("projects")

    def test_basic(self):
        """
        Test retrieval of allowed projects, actions and scopes.
        """

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["data"],
            [
                {
                    "project": self.project.code,
                    "name": self.project.name,
                    "scope": "analyst",
                    "actions": [
                        "get",
                        "list",
                        "filter",
                        "history",
                    ],
                }
            ],
        )
