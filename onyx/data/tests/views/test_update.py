from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data
from ...exceptions import ClimbIDNotFound
from projects.testproject.models import TestModel


# TODO: Tests for update endpoint
class TestUpdateView(OnyxTestCase):
    def setUp(self):
        super().setUp()
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
                "projects.testproject.test.climb_id",
                kwargs={"code": self.project.code, "climb_id": self.climb_id},
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

    def test_climb_id_not_found(self):
        """
        Test update of a record by CLIMB ID that does not exist.
        """

        prefix, postfix = self.climb_id.split("-")
        climb_id_not_found = "-".join([prefix, postfix[::-1]])
        response = self.client.patch(self.endpoint(climb_id_not_found), data={})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.json()["messages"]["detail"], ClimbIDNotFound.default_detail
        )

    def test_empty_payload_success(self):
        """
        Test that an empty payload passes.
        """

        for payload in [None, {}]:
            response = self.client.patch(self.endpoint(self.climb_id), data=payload)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bad_request(self):
        """
        Test that a badly structured payload fails.
        """

        for payload in [
            "",
            "hi",
            0,
            [],
            {"records": ""},
            {"records": "hi"},
            {"records": 0},
            {"records": {}},
            {"sample_id": []},
            {None: {}},
            {"records": [[[[[[[[]]]]]]]]},
        ]:
            response = self.client.patch(self.endpoint(self.climb_id), data=payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unpermissioned_viewable_field(self):
        """
        Test that a payload with an unpermissioned viewable field fails.
        """

        response = self.client.patch(
            self.endpoint(self.climb_id), data={"climb_id": "helloooo"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        instance = TestModel.objects.get(climb_id=self.climb_id)
        self.assertEqual(instance.climb_id, self.climb_id)
