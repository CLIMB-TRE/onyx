from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxDataTestCase
from projects.testproject.models import TestModel


# TODO: Tests for query endpoint


class TestQueryView(OnyxDataTestCase):
    def setUp(self):
        """
        Create a user with the required permissions and create a set of test records.
        """

        super().setUp()
        self.endpoint = reverse(
            "projects.testproject.query", kwargs={"code": self.project.code}
        )

    def test_basic(self):
        """
        Test basic retrieval of all records.
        """

        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqualClimbIDs(
            response.json()["data"],
            TestModel.objects.all(),
        )
