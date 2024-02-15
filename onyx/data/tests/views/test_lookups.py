from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase
from ...types import OnyxType


class TestLookupsView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions.
        """

        super().setUp()
        self.endpoint = reverse("data.project.lookups", kwargs={"code": "test"})
        self.user = self.setup_user(
            "testuser", roles=["is_staff"], groups=["test.admin"]
        )

    def test_basic(self):
        """
        Test retrieval of available lookups for a project.
        """

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lookups = {onyx_type.label: onyx_type.lookups for onyx_type in OnyxType}
        self.assertEqual(response.json()["data"], lookups)
