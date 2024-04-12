from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase
from ...actions import Actions


class TestProjectsView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions.
        """

        super().setUp()
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
                    "project": "testproject",
                    "scope": "admin",
                    "actions": [action.value for action in Actions],
                }
            ],
        )
