from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase


class TestFieldsView(OnyxTestCase):
    def setUp(self):
        super().setUp()
        self.endpoint = reverse(
            "projects.testproject.fields", kwargs={"code": self.project.code}
        )

    def test_basic(self):
        """
        Test retrieval of fields specification for a project.
        """

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
