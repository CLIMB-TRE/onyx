from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data
from ...models.projects.test import TestModel


# TODO: Tests for delete endpoint
class TestDeleteView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions and create a test record.
        """

        super().setUp()
        self.endpoint = lambda climb_id: reverse(
            "data.project.climb_id", kwargs={"code": "test", "climb_id": climb_id}
        )
        self.user = self.setup_user(
            "testuser", roles=["is_staff"], groups=["test.admin"]
        )
        response = self.client.post(
            reverse("data.project", kwargs={"code": "test"}),
            data=next(iter(generate_test_data(n=1))),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.climb_id = response.json()["data"]["climb_id"]

    def test_basic(self):
        """
        Test deletion of a record by CLIMB ID.
        """

        response = self.client.delete(self.endpoint(self.climb_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(TestModel.objects.filter(climb_id=self.climb_id).exists())
