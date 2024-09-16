from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxDataTestCase
from projects.testproject.models import TestModel


class TestCountView(OnyxDataTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the analyst user
        self.client.force_authenticate(self.analyst_user)  # type: ignore

        self.filter_endpoint = reverse(
            "projects.testproject.count", kwargs={"code": self.project.code}
        )
        self.query_endpoint = reverse(
            "projects.testproject.query.count", kwargs={"code": self.project.code}
        )

    def test_basic(self):
        """
        Test counting records.
        """

        response = self.client.get(self.filter_endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"], {"count": TestModel.objects.count()})

        response = self.client.post(self.query_endpoint, data={})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"], {"count": TestModel.objects.count()})
