from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data


# TODO: Tests for identify endpoint
class TestIdentifyView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions and create a test record.
        """

        super().setUp()
        self.endpoint = lambda field: reverse(
            "data.project.identify", kwargs={"code": "test", "field": field}
        )
        self.user = self.setup_user(
            "testuser", roles=["is_staff"], groups=["test.test"]
        )
        test_record = next(iter(generate_test_data(n=1)))
        self.input_sample_id = test_record["sample_id"]
        self.input_run_name = test_record["run_name"]
        response = self.client.post(
            reverse("data.project", kwargs={"code": "test"}),
            data=test_record,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.output_sample_id = response.json()["data"]["sample_id"]
        self.output_run_name = response.json()["data"]["run_name"]

    def test_basic(self):
        """
        Test retrieving identifiers for anonymised fields.
        """

        response = self.client.post(
            self.endpoint("sample_id"), data={"value": self.input_sample_id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["identifier"], self.output_sample_id)

        response = self.client.post(
            self.endpoint("run_name"), data={"value": self.input_run_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["identifier"], self.output_run_name)
