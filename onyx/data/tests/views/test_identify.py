import hashlib
from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data
from ...exceptions import IdentifierNotFound
from data.models import Anonymiser
from projects.testproject.models import TestModel


# TODO: Test permissions to retrieve identifiers for users from different sites


class TestIdentifyView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user
        self.client.force_authenticate(self.admin_staff)  # type: ignore

        self.endpoint = lambda field: reverse(
            "projects.testproject.identify.field",
            kwargs={"code": self.project.code, "field": field},
        )

    def test_basic(self):
        """
        Test creating/retrieving identifiers for anonymised fields.
        """

        # Create records from testsite_1 and testsite_2
        test_record_1 = next(iter(generate_test_data(n=1)))
        test_record_2 = next(iter(generate_test_data(n=1)))
        test_record_2["site"] = self.extra_site.code

        for i, (record, site) in enumerate(
            [
                (test_record_1, self.site),
                (test_record_2, self.extra_site),
            ],
            start=1,
        ):
            result = self.client.post(
                reverse("projects.testproject", kwargs={"code": self.project.code}),
                data=record,
            )
            self.assertEqual(result.status_code, status.HTTP_201_CREATED)
            for field in ["sample_id", "run_name"]:
                # Get the returned identifier
                identifier = result.json()["data"][field]

                # Check that the value has been anonymised
                hasher = hashlib.sha256()
                hasher.update(record[field].strip().lower().encode("utf-8"))
                hash = hasher.hexdigest()
                self.assertEqual(
                    Anonymiser.objects.get(
                        project=self.project,
                        site=site,
                        field=field,
                        hash=hash,
                    ).identifier,
                    identifier,
                )

                # Identify the value
                response = self.client.post(
                    self.endpoint(field),
                    data={
                        "value": record[field],
                        "site": site.code,
                    },
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    response.json()["data"],
                    {
                        "project": self.project.code,
                        "site": site.code,
                        "field": field,
                        "value": record[field],
                        "identifier": identifier,
                    },
                )

            self.assertEqual(Anonymiser.objects.count(), i * 2)

    def test_same_value_same_site(self):
        """
        Test that the same value from the same site is assigned the same identifier.
        """

        iterator = iter(generate_test_data(n=2))
        test_record_1 = next(iterator)
        response = self.client.post(
            reverse("projects.testproject", kwargs={"code": self.project.code}),
            data=test_record_1,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        output_sample_id_1 = response.json()["data"]["sample_id"]
        output_run_name_1 = response.json()["data"]["run_name"]

        test_record_2 = next(iterator)
        test_record_2["run_name"] = test_record_1["run_name"]
        response = self.client.post(
            reverse("projects.testproject", kwargs={"code": self.project.code}),
            data=test_record_2,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        output_sample_id_2 = response.json()["data"]["sample_id"]
        output_run_name_2 = response.json()["data"]["run_name"]

        self.assertNotEqual(test_record_1["sample_id"], test_record_2["sample_id"])
        self.assertNotEqual(output_sample_id_1, output_sample_id_2)
        self.assertEqual(test_record_1["run_name"], test_record_2["run_name"])
        self.assertEqual(output_run_name_1, output_run_name_2)
        assert TestModel.objects.count() == 2
        assert Anonymiser.objects.count() == 3
        assert Anonymiser.objects.filter(site__code="testsite_1").count() == 3
        assert Anonymiser.objects.filter(field="sample_id").count() == 2
        assert Anonymiser.objects.filter(field="run_name").count() == 1
        assert Anonymiser.objects.filter(identifier=output_sample_id_1).count() == 1
        assert Anonymiser.objects.filter(identifier=output_sample_id_2).count() == 1
        assert Anonymiser.objects.filter(identifier=output_run_name_1).count() == 1

    def test_same_value_different_site(self):
        """
        Test that the same values from different sites are assigned different identifiers.
        """

        iterator = iter(generate_test_data(n=2))
        test_record_1 = next(iterator)
        response = self.client.post(
            reverse("projects.testproject", kwargs={"code": self.project.code}),
            data=test_record_1,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        output_sample_id_1 = response.json()["data"]["sample_id"]
        output_run_name_1 = response.json()["data"]["run_name"]

        test_record_2 = next(iterator)
        test_record_2["site"] = self.extra_site.code
        test_record_2["sample_id"] = test_record_1["sample_id"]
        test_record_2["run_name"] = test_record_1["run_name"]
        response = self.client.post(
            reverse("projects.testproject", kwargs={"code": self.project.code}),
            data=test_record_2,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        output_sample_id_2 = response.json()["data"]["sample_id"]
        output_run_name_2 = response.json()["data"]["run_name"]

        self.assertEqual(test_record_1["sample_id"], test_record_2["sample_id"])
        self.assertEqual(test_record_1["run_name"], test_record_2["run_name"])
        self.assertNotEqual(output_sample_id_1, output_sample_id_2)
        self.assertNotEqual(output_run_name_1, output_run_name_2)

        assert TestModel.objects.count() == 2
        assert Anonymiser.objects.count() == 4
        assert Anonymiser.objects.filter(site__code="testsite_1").count() == 2
        assert Anonymiser.objects.filter(site__code="testsite_2").count() == 2
        assert Anonymiser.objects.filter(field="sample_id").count() == 2
        assert Anonymiser.objects.filter(field="run_name").count() == 2
        assert Anonymiser.objects.filter(identifier=output_sample_id_1).count() == 1
        assert Anonymiser.objects.filter(identifier=output_sample_id_2).count() == 1
        assert Anonymiser.objects.filter(identifier=output_run_name_1).count() == 1
        assert Anonymiser.objects.filter(identifier=output_run_name_2).count() == 1

    def test_unknown_field(self):
        """
        Test failure to identify an unknown field.
        """

        response = self.client.post(
            self.endpoint("unknown"),
            data={
                "value": "test",
                "site": self.site.code,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bad_request_body(self):
        """
        Test failure to identify a field with a bad request body.
        """

        # TODO: Test more bad request body cases
        response = self.client.post(
            self.endpoint("sample_id"),
            data={
                "site": self.site.code,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_identifier_not_found(self):
        """
        Test failure to identify a field with an unknown value.
        """

        response = self.client.post(
            self.endpoint("sample_id"),
            data={
                "value": "unknown",
                "site": self.site.code,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.json()["messages"]["detail"], IdentifierNotFound.default_detail
        )
