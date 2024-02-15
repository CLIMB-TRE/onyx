from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase


class TestChoicesView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions.
        """

        super().setUp()
        self.endpoint = lambda field: reverse(
            "data.project.choices", kwargs={"code": "test", "field": field}
        )
        self.user = self.setup_user(
            "testuser", roles=["is_staff"], groups=["test.admin"]
        )

    def test_basic(self):
        """
        Test retrieval of choices for a choice field.
        """

        response = self.client.get(self.endpoint("country"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.json()["data"]), {"eng", "wales", "scot", "ni"})
