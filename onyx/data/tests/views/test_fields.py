from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase


class TestFieldsView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions.
        """

        super().setUp()
        self.endpoint = reverse("data.project.fields", kwargs={"code": "test"})
        self.user = self.setup_user(
            "testuser", roles=["is_staff"], groups=["test.admin"]
        )

    def test_basic(self):
        """
        Test retrieval of fields specification for a project.
        """

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
