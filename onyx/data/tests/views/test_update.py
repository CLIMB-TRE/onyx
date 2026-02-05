from datetime import datetime
import copy
from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data
from ...exceptions import ClimbIDNotFound
from data.models import Anonymiser, Analysis
from projects.testproject.models import TestProject
from .test_create import default_payload


# TODO: Test failing to update a record in a different site


class TestUpdateView(OnyxTestCase):
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
        Test update of a record by CLIMB ID.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        assert instance.tests is not None
        updated_values = {
            "tests": instance.tests + 1,
            "text_option_2": instance.text_option_2 + "!",
        }
        response = self.client.patch(self.endpoint(self.climb_id), data=updated_values)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_instance = TestProject.objects.get(climb_id=self.climb_id)
        self.assertEqual(updated_instance.tests, updated_values["tests"])
        self.assertEqual(
            updated_instance.text_option_2, updated_values["text_option_2"]
        )

    def test_basic_test(self):
        """
        Test the test update of a record by CLIMB ID.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
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
        updated_instance = TestProject.objects.get(climb_id=self.climb_id)
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
        instance = TestProject.objects.get(climb_id=self.climb_id)
        self.assertEqual(instance.climb_id, self.climb_id)

    def test_unknown_fields(self):
        """
        Test that a payload with unknown fields fails.
        """

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"unknown_field": "value", "another_unknown": 123},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "unknown_field", status_code=400)
        self.assertContains(response, "another_unknown", status_code=400)

    def test_unknown_nested_fields(self):
        """
        Test that a payload with unknown nested fields fails.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.records.create(  # type: ignore
            user=self.admin_user,  # type: ignore
            test_id=500,
            test_pass=False,
            test_start=datetime.now().date(),
            test_end=datetime.now().date(),
            score_a=1.0,
            score_b=2.0,
        )

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"records": [{"test_id": 500, "unknown_field": "value"}]},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "records__unknown_field", status_code=400)

    def test_admin_can_update_suppressed(self):
        """
        Test that admin users can still update suppressed records.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.is_suppressed = True
        instance.save()

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"tests": 100},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertEqual(instance.tests, 100)

    def test_admin_can_update_unpublished(self):
        """
        Test that admin users can still update unpublished records.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.is_published = False
        instance.save()

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"tests": 100},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertEqual(instance.tests, 100)

    def test_analyst_cannot_update(self):
        """
        Test that an analyst user cannot update records.
        """

        self.client.force_authenticate(self.analyst_user)  # type: ignore

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"tests": 100},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_update(self):
        """
        Test that an unauthenticated user cannot update records.
        """

        self.client.force_authenticate(None)  # type: ignore

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"tests": 100},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unique_together(self):
        """
        Test that a unique together constraint is enforced on update.
        """

        # Create a second record
        payload = copy.deepcopy(default_payload)
        payload["sample_id"] = "sample-9999"
        payload["run_name"] = "run-9999"
        payload["unique_together_1"] = "unique9999"
        payload["unique_together_2"] = "unique9999"
        response = self.client.post(
            reverse("projects.testproject", kwargs={"code": self.project.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        second_climb_id = response.json()["data"]["climb_id"]

        # Try to update the second record to have the same unique_together_1/unique_together_2 as the first
        first_instance = TestProject.objects.get(climb_id=self.climb_id)
        response = self.client.patch(
            self.endpoint(second_climb_id),
            data={
                "unique_together_1": first_instance.unique_together_1,
                "unique_together_2": first_instance.unique_together_2,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "unique_together_1", status_code=400)
        self.assertContains(response, "unique_together_2", status_code=400)

    def test_ordering(self):
        """
        Test that an ordering constraint is enforced on update.
        """

        # start must be less than end
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"start": 10, "end": 5},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "start", status_code=400)
        self.assertContains(response, "end", status_code=400)

    def test_conditional_required_fields(self):
        """
        Test that a conditional required constraint is enforced on update.
        """

        # region requires country
        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.country = ""
        instance.region = ""
        instance.save()

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"region": "other"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "region", status_code=400)

    def test_optional_value_group(self):
        """
        Test that an optional value group constraint is enforced on update.
        """

        # Initially both have values - verify we can clear one at a time
        # Clear text_option_1 while text_option_2 still has a value
        response = self.client.patch(
            f"{self.endpoint(self.climb_id)}?clear=text_option_1"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Now try to clear text_option_2 as well - this should fail because
        # at least one of the fields must have a value
        response = self.client.patch(
            f"{self.endpoint(self.climb_id)}?clear=text_option_2"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "text_option_1", status_code=400)
        self.assertContains(response, "text_option_2", status_code=400)

    def test_max_length(self):
        """
        Test that max length constraint is enforced on update.
        """

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"char_max_length_20": "X" * 21},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "char_max_length_20", status_code=400)

    def test_invalid_choice(self):
        """
        Test that invalid choice values are rejected.
        """

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"country": "invalid_country"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "country", status_code=400)

    def test_invalid_date_format(self):
        """
        Test that invalid date formats are rejected.
        """

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"collection_month": "not-a-date"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "collection_month", status_code=400)

    def test_invalid_integer(self):
        """
        Test that invalid integer values are rejected.
        """

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"tests": "not-an-integer"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "tests", status_code=400)

    def test_invalid_decimal(self):
        """
        Test that invalid decimal values are rejected.
        """

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"score": "not-a-decimal"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "score", status_code=400)

    def test_invalid_boolean(self):
        """
        Test that invalid boolean values are rejected.
        """

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"concern": "not-a-boolean"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "concern", status_code=400)

    def test_update_preserves_unmodified_fields(self):
        """
        Test that updating some fields preserves other fields.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        original_sample_id = instance.sample_id
        original_run_name = instance.run_name

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"tests": 999},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertEqual(instance.tests, 999)
        self.assertEqual(instance.sample_id, original_sample_id)
        self.assertEqual(instance.run_name, original_run_name)

    def test_update_nested_preserves_other_nested(self):
        """
        Test that updating one nested record preserves other nested records.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.records.create(  # type: ignore
            user=self.admin_user,  # type: ignore
            test_id=100,
            test_pass=False,
            test_start=datetime.now().date(),
            test_end=datetime.now().date(),
            score_a=1.0,
            score_b=2.0,
        )
        instance.records.create(  # type: ignore
            user=self.admin_user,  # type: ignore
            test_id=200,
            test_pass=True,
            test_start=datetime.now().date(),
            test_end=datetime.now().date(),
            test_result="original",
            score_a=3.0,
            score_b=4.0,
        )

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={
                "records": [
                    {"test_id": 100, "test_pass": True, "test_result": "updated"}
                ]
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        record_100 = instance.records.get(test_id=100)  # type: ignore
        record_200 = instance.records.get(test_id=200)  # type: ignore
        self.assertTrue(record_100.test_pass)
        self.assertEqual(record_100.test_result, "updated")
        self.assertTrue(record_200.test_pass)
        self.assertEqual(record_200.test_result, "original")

    def test_nested_unique_together(self):
        """
        Test that a nested unique together constraint is enforced on update.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        records_count = instance.records.count()  # type: ignore
        test_nested_record = {
            "test_id": 100,
            "test_pass": False,
            "test_start": "2023-01",
            "test_end": "2023-02",
            "score_a": 1.0,
            "score_b": 2.0,
        }

        # Try to update record 200 to have the same test_id as record 100
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"records": [test_nested_record, test_nested_record]},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "test_id", status_code=400)
        self.assertContains(response, "unique", status_code=400)

        # The original records should still exist unchanged
        instance.refresh_from_db()
        self.assertEqual(instance.records.count(), records_count)  # type: ignore

    def test_nested_ordering(self):
        """
        Test that a nested ordering constraint is enforced on update.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.records.create(  # type: ignore
            user=self.admin_user,  # type: ignore
            test_id=100,
            test_pass=False,
            test_start=datetime(2023, 1, 1).date(),
            test_end=datetime(2023, 6, 1).date(),
            score_a=1.0,
            score_b=2.0,
        )

        # test_start must be before test_end
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={
                "records": [
                    {"test_id": 100, "test_start": "2023-06", "test_end": "2023-01"}
                ]
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "test_start", status_code=400)
        self.assertContains(response, "test_end", status_code=400)

    def test_nested_conditional_value_required_fields(self):
        """
        Test that a nested conditional value required constraint is enforced on update.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.records.create(  # type: ignore
            user=self.admin_user,  # type: ignore
            test_id=100,
            test_pass=False,
            test_start=datetime.now().date(),
            test_end=datetime.now().date(),
            score_a=1.0,
            score_b=2.0,
        )

        # test_pass=True requires test_result
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"records": [{"test_id": 100, "test_pass": True}]},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "test_pass", status_code=400)
        self.assertContains(response, "test_result", status_code=400)

    def test_update_text(self):
        """
        Test updating a text field.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)

        # Update with a new value
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"text_option_2": "updated text value"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertEqual(instance.text_option_2, "updated text value")

        # Update with whitespace (should be stripped)
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"text_option_2": "  trimmed  "},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertEqual(instance.text_option_2, "trimmed")

        # Update with empty string
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"text_option_2": ""},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertEqual(instance.text_option_2, "")

    def test_clear_text(self):
        """
        Test clearing a text field sets it to an empty string.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.text_option_2 = "some text"
        instance.save()
        instance.refresh_from_db()
        self.assertNotEqual(instance.text_option_2, "")

        response = self.client.patch(
            f"{self.endpoint(self.climb_id)}?clear=text_option_2"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertEqual(instance.text_option_2, "")

    def test_update_choice(self):
        """
        Test updating a choice field.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)

        # Update with a valid choice
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"region": "ne"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertEqual(instance.region, "ne")

        # Update with different case (should be normalized)
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"region": "NW"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertEqual(instance.region, "nw")

        # Update with empty string
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"region": ""},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertEqual(instance.region, "")

        # Update with invalid choice should fail
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"region": "invalid_choice"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "region", status_code=400)

    def test_clear_choice(self):
        """
        Test clearing a choice field sets it to an empty string.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.country = "eng"
        instance.region = "london"
        instance.save()
        instance.refresh_from_db()
        self.assertNotEqual(instance.country, "")
        self.assertNotEqual(instance.region, "")

        response = self.client.patch(
            f"{self.endpoint(self.climb_id)}?clear=country&clear=region"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertEqual(instance.country, "")
        self.assertEqual(instance.region, "")

    def test_update_integer(self):
        """
        Test updating an integer field.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)

        # Update with a new value
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"tests": 42},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertEqual(instance.tests, 42)

        # Update with string representation
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"tests": "100"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertEqual(instance.tests, 100)

        # Update with null
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"tests": None},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertIsNone(instance.tests)

        # Update with invalid value should fail
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"tests": "not_a_number"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "tests", status_code=400)

    def test_clear_integer(self):
        """
        Test clearing an integer field sets it to null.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.tests = 5
        instance.save()
        instance.refresh_from_db()
        self.assertIsNotNone(instance.tests)

        response = self.client.patch(f"{self.endpoint(self.climb_id)}?clear=tests")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertIsNone(instance.tests)

    def test_update_decimal(self):
        """
        Test updating a decimal field.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)

        # Update with a new value
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"score": 3.14159},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertIsNotNone(instance.score)
        self.assertAlmostEqual(instance.score, 3.14159, places=5)  # type: ignore

        # Update with string representation
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"score": "99.99"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertIsNotNone(instance.score)
        self.assertAlmostEqual(instance.score, 99.99, places=2)  # type: ignore

        # Update with integer (should work as decimal)
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"score": 100},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertEqual(instance.score, 100.0)

        # Update with null
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"score": None},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertIsNone(instance.score)

        # Update with invalid value should fail
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"score": "not_a_number"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "score", status_code=400)

    def test_clear_decimal(self):
        """
        Test clearing a decimal field sets it to null.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.score = 3.14
        instance.save()
        instance.refresh_from_db()
        self.assertIsNotNone(instance.score)

        response = self.client.patch(f"{self.endpoint(self.climb_id)}?clear=score")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertIsNone(instance.score)

    def test_update_date(self):
        """
        Test updating a date field.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)

        # Update with a new value
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"submission_date": "2024-06-15"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertIsNotNone(instance.submission_date)
        self.assertEqual(instance.submission_date.strftime("%Y-%m-%d"), "2024-06-15")  # type: ignore

        # Update with different format
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"submission_date": "2024-1-5"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertIsNotNone(instance.submission_date)
        self.assertEqual(instance.submission_date.strftime("%Y-%m-%d"), "2024-01-05")  # type: ignore

        # Update with null
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"submission_date": None},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertIsNone(instance.submission_date)

        # Update with invalid value should fail
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"submission_date": "not_a_date"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "submission_date", status_code=400)

    def test_clear_date(self):
        """
        Test clearing a date field sets it to null.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.collection_month = datetime(2023, 1, 15).date()
        instance.received_month = datetime(2023, 2, 20).date()
        instance.save()
        instance.refresh_from_db()
        self.assertIsNotNone(instance.collection_month)

        response = self.client.patch(
            f"{self.endpoint(self.climb_id)}?clear=collection_month"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertIsNone(instance.collection_month)
        self.assertIsNotNone(instance.received_month)

        # Test at least one required constraint fails when clearing
        instance.received_month = datetime.now().date()
        instance.save()
        instance.refresh_from_db()
        self.assertIsNotNone(instance.received_month)

        response = self.client.patch(
            f"{self.endpoint(self.climb_id)}?clear=received_month"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        instance.refresh_from_db()
        self.assertIsNotNone(instance.received_month)

    def test_update_bool(self):
        """
        Test updating a boolean field.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)

        # Update with True
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"concern": True},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertTrue(instance.concern)

        # Update with False
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"concern": False},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertFalse(instance.concern)

        # Update with string "true"
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"concern": "true"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertTrue(instance.concern)

        # Update with string "false"
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"concern": "false"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertFalse(instance.concern)

        # Update with null
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"concern": None},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertIsNone(instance.concern)

        # Update with invalid value should fail
        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"concern": "not_a_bool"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "concern", status_code=400)

    def test_clear_bool(self):
        """
        Test clearing a boolean field sets it to null.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.concern = True
        instance.save()
        instance.refresh_from_db()
        self.assertIsNotNone(instance.concern)

        response = self.client.patch(f"{self.endpoint(self.climb_id)}?clear=concern")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertIsNone(instance.concern)

    def test_update_array(self):
        """
        Test updating an array field.
        """

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"scores": "[1, 2, 3, 4, 5]"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance = TestProject.objects.get(climb_id=self.climb_id)
        self.assertEqual(instance.scores, [1, 2, 3, 4, 5])

    def test_clear_array(self):
        """
        Test clearing an array field sets it to an empty list.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.scores = [1, 2, 3]
        instance.save()
        instance.refresh_from_db()
        self.assertIsNotNone(instance.scores)

        response = self.client.patch(f"{self.endpoint(self.climb_id)}?clear=scores")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertEqual(instance.scores, [])

    def test_update_structure(self):
        """
        Test updating a structure (JSON) field.
        """

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={"structure": '{"key": "value", "nested": {"number": 42}}'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance = TestProject.objects.get(climb_id=self.climb_id)
        self.assertEqual(instance.structure, {"key": "value", "nested": {"number": 42}})

    def test_clear_structure(self):
        """
        Test clearing a structure (JSON) field sets it to an empty dict.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.structure = {"key": "value", "nested": {"number": 42}}
        instance.save()
        instance.refresh_from_db()
        self.assertIsNotNone(instance.structure)

        response = self.client.patch(f"{self.endpoint(self.climb_id)}?clear=structure")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertEqual(instance.structure, {})

    def test_update_analysis_identifiers(self):
        """
        Test updating an identifiers field on an analysis.
        """

        # Create test identifiers
        identifier_1 = Anonymiser.objects.create(
            project=self.project,
            site=self.site,
            field="test_field",
            hash="test_hash_1",
            prefix="I-",
        )
        identifier_2 = Anonymiser.objects.create(
            project=self.project,
            site=self.site,
            field="test_field",
            hash="test_hash_2",
            prefix="I-",
        )
        identifier_3 = Anonymiser.objects.create(
            project=self.project,
            site=self.site,
            field="test_field",
            hash="test_hash_3",
            prefix="I-",
        )

        # Create an analysis with the first identifier
        analysis_payload = {
            "name": "Test Analysis",
            "analysis_date": "2024-01-01",
            "pipeline_name": "Test Pipeline",
            "pipeline_version": "0.1.0",
            "result": "Test Result",
            "report": "s3://test-bucket/test-report.html",
            "identifiers": [identifier_1.identifier],
        }
        response = self.client.post(
            reverse(
                "projects.testproject.analysis",
                kwargs={"code": self.project.code},
            ),
            data=analysis_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        analysis_id = response.json()["data"]["analysis_id"]

        # Verify the analysis has the first identifier
        instance = Analysis.objects.get(analysis_id=analysis_id)
        self.assertEqual(instance.identifiers.count(), 1)
        self.assertIn(identifier_1, instance.identifiers.all())

        # Update the identifiers to a new set
        response = self.client.patch(
            reverse(
                "projects.testproject.analysis.analysis_id",
                kwargs={"code": self.project.code, "analysis_id": analysis_id},
            ),
            data={"identifiers": [identifier_2.identifier, identifier_3.identifier]},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the identifiers have been updated
        instance.refresh_from_db()
        self.assertEqual(instance.identifiers.count(), 2)
        self.assertNotIn(identifier_1, instance.identifiers.all())
        self.assertIn(identifier_2, instance.identifiers.all())
        self.assertIn(identifier_3, instance.identifiers.all())

    def test_clear_analysis_identifiers(self):
        """
        Test clearing an identifiers field on an analysis sets it to an empty list.
        """

        # Create test identifier
        identifier = Anonymiser.objects.create(
            project=self.project,
            site=self.site,
            field="test_field",
            hash="test_hash",
            prefix="I-",
        )

        # Create an analysis with the identifier
        analysis_payload = {
            "name": "Test Analysis",
            "analysis_date": "2024-01-01",
            "pipeline_name": "Test Pipeline",
            "pipeline_version": "0.1.0",
            "result": "Test Result",
            "report": "s3://test-bucket/test-report.html",
            "identifiers": [identifier.identifier],
        }
        response = self.client.post(
            reverse(
                "projects.testproject.analysis",
                kwargs={"code": self.project.code},
            ),
            data=analysis_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        analysis_id = response.json()["data"]["analysis_id"]

        # Verify the analysis has the identifier
        instance = Analysis.objects.get(analysis_id=analysis_id)
        self.assertEqual(instance.identifiers.count(), 1)

        # Clear the identifiers field
        response = self.client.patch(
            reverse(
                "projects.testproject.analysis.analysis_id",
                kwargs={"code": self.project.code, "analysis_id": analysis_id},
            )
            + "?clear=identifiers"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the identifiers are now empty
        instance.refresh_from_db()
        self.assertEqual(instance.identifiers.count(), 0)

    def test_add_nested_record(self):
        """
        Test adding a new nested record during update.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        initial_count = instance.records.count()  # type: ignore

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={
                "records": [
                    {
                        "test_id": 999,
                        "test_pass": False,
                        "test_start": "2023-01",
                        "test_end": "2023-02",
                        "score_a": 1.0,
                        "score_b": 2.0,
                    }
                ]
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertEqual(instance.records.count(), initial_count + 1)  # type: ignore
        self.assertTrue(instance.records.filter(test_id=999).exists())  # type: ignore

    def test_update_nested_record(self):
        """
        Test updating an existing nested record.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.records.create(  # type: ignore
            user=self.admin_user,  # type: ignore
            test_id=500,
            test_pass=False,
            test_start=datetime.now().date(),
            test_end=datetime.now().date(),
            score_a=1.0,
            score_b=2.0,
        )
        instance.refresh_from_db()
        nested_record = instance.records.get(test_id=500)  # type: ignore

        response = self.client.patch(
            self.endpoint(self.climb_id),
            data={
                "records": [
                    {"test_id": 500, "test_pass": True, "test_result": "updated"}
                ]
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        nested_record.refresh_from_db()
        self.assertTrue(nested_record.test_pass)
        self.assertEqual(nested_record.test_result, "updated")

    def test_clear_nested_records(self):
        """
        Test clearing a relation field deletes all related objects.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.records.create(  #  type: ignore
            user=self.admin_user,  # type: ignore
            test_id=1000,
            test_pass=False,
            test_start=datetime.now().date(),
            test_end=datetime.now().date(),
            score_a=95.0,
        )
        instance.refresh_from_db()
        self.assertGreater(instance.records.count(), 0)  #  type: ignore

        response = self.client.patch(f"{self.endpoint(self.climb_id)}?clear=records")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertEqual(instance.records.count(), 0)  #  type: ignore

    def test_clear_multiple_fields(self):
        """
        Test clearing multiple fields at once.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.tests = 10
        instance.score = 5.5
        instance.text_option_2 = "some text"
        instance.save()

        response = self.client.patch(
            f"{self.endpoint(self.climb_id)}?clear=tests&clear=score&clear=text_option_2",
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance.refresh_from_db()
        self.assertIsNone(instance.tests)
        self.assertIsNone(instance.score)
        self.assertEqual(instance.text_option_2, "")

    def test_clear_with_update(self):
        """
        Test clearing fields while also updating other fields.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.tests = 10
        instance.score = 5.5
        instance.save()

        response = self.client.patch(
            f"{self.endpoint(self.climb_id)}?clear=score",
            data={"tests": 20},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertEqual(instance.tests, 20)
        self.assertIsNone(instance.score)

    def test_clear_unknown_field(self):
        """
        Test that clearing an unknown field fails.
        """

        response = self.client.patch(
            f"{self.endpoint(self.climb_id)}?clear=unknown_field"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "unknown_field", status_code=400)

    def test_clear_nested_field_fails(self):
        """
        Test that clearing a nested field (with __) fails.
        """

        response = self.client.patch(
            f"{self.endpoint(self.climb_id)}?clear=records__test_id"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertContains(response, "records__test_id", status_code=400)

    def test_clear_test(self):
        """
        Test that clearing in test mode does not actually clear the fields.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        original_value = instance.text_option_2

        response = self.client.patch(
            reverse(
                "projects.testproject.test.climb_id",
                kwargs={"code": self.project.code, "climb_id": self.climb_id},
            )
            + "?clear=text_option_2"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"], {})
        instance.refresh_from_db()
        self.assertEqual(instance.text_option_2, original_value)
