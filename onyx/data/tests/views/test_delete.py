from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data
from projects.testproject.models import TestProject


# TODO: Tests for delete endpoint
# TODO: Test failing to delete a record in a different site


class TestDeleteView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user
        self.client.force_authenticate(self.admin_user)  # type: ignore

        self.endpoint = lambda climb_id: reverse(
            "projects.testproject.climb_id",
            kwargs={"code": self.project.code, "climb_id": climb_id},
        )
        response = self.client.post(
            reverse("projects.testproject", kwargs={"code": self.project.code}),
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
        self.assertFalse(TestProject.objects.filter(climb_id=self.climb_id).exists())

    def test_climb_id_not_found(self):
        """
        Test deletion of a record by CLIMB ID that does not exist.
        """

        prefix, postfix = self.climb_id.split("-")
        climb_id_not_found = "-".join([prefix, postfix[::-1]])
        response = self.client.delete(self.endpoint(climb_id_not_found))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(TestProject.objects.filter(climb_id=self.climb_id).exists())
