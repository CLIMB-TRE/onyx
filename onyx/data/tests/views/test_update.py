from datetime import datetime
import copy
from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data
from ...exceptions import ClimbIDNotFound
from data.models import Anonymiser, Analysis
from projects.testproject.models import TestProject
from .test_create import default_payload


# TODO: Tests for update endpoint
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

    def test_clear_relation(self):
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

    def test_clear_nested_field_fails(self):
        """
        Test that clearing a nested field (with __) fails.
        """

        response = self.client.patch(
            f"{self.endpoint(self.climb_id)}?clear=records__test_id"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
