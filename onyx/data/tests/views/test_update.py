from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data
from ...models.projects.test import TestModel


# TODO: Tests for update endpoint
class TestUpdateView(OnyxTestCase):
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
        Test update of a record by CLIMB ID.
        """

        instance = TestModel.objects.get(climb_id=self.climb_id)
        assert instance.tests is not None
        updated_values = {
            "tests": instance.tests + 1,
            "text_option_2": instance.text_option_2 + "!",
        }
        response = self.client.patch(self.endpoint(self.climb_id), data=updated_values)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_instance = TestModel.objects.get(climb_id=self.climb_id)
        self.assertEqual(updated_instance.tests, updated_values["tests"])
        self.assertEqual(
            updated_instance.text_option_2, updated_values["text_option_2"]
        )

    def test_basic_test(self):
        """
        Test the test update of a record by CLIMB ID.
        """

        instance = TestModel.objects.get(climb_id=self.climb_id)
        assert instance.tests is not None
        original_values = {
            "tests": instance.tests,
            "text_option_2": instance.text_option_2,
        }
        updated_values = {
            "tests": instance.tests + 1,
            "text_option_2": instance.text_option_2 + "!",
        }
        response = self.client.patch(
            reverse(
                "data.project.test.climb_id",
                kwargs={"code": "test", "climb_id": self.climb_id},
            ),
            data=updated_values,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"], {})
        updated_instance = TestModel.objects.get(climb_id=self.climb_id)
        self.assertEqual(updated_instance.tests, original_values["tests"])
        self.assertEqual(
            updated_instance.text_option_2, original_values["text_option_2"]
        )
