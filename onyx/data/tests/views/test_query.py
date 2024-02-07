from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data


# TODO: Tests for query endpoint


class TestQueryView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions and create a set of test records.
        """

        super().setUp()
        self.endpoint = reverse("data.project.query", kwargs={"code": "test"})
        self.user = self.setup_user(
            "testuser", roles=["is_staff"], groups=["test.test"]
        )
        for payload in generate_test_data():
            response = self.client.post(
                reverse("data.project", kwargs={"code": "test"}), data=payload
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
