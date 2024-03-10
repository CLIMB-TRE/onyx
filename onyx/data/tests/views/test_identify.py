from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data
from data.models import Anonymiser
from projects.testproject.models import TestModel


class TestIdentifyView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions and create a test record.
        """

        super().setUp()
        self.endpoint = lambda field: reverse(
            "project.testproject.identify",
            kwargs={"code": "testproject", "field": field},
        )
        self.user = self.setup_user(
            "testuser", roles=["is_staff"], groups=["testproject.admin"]
        )

    def test_basic(self):
        """
        Test creating/retrieving identifiers for anonymised fields.
        """

        # Create record from testsite_1
        test_record_1 = next(iter(generate_test_data(n=1)))
        response = self.client.post(
            reverse("project.testproject", kwargs={"code": "testproject"}),
            data=test_record_1,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        output_sample_id_1 = response.json()["data"]["sample_id"]
        output_run_name_1 = response.json()["data"]["run_name"]

        assert TestModel.objects.count() == 1
        assert Anonymiser.objects.count() == 2
        assert Anonymiser.objects.filter(site__code="testsite_1").count() == 2
        assert Anonymiser.objects.filter(field="sample_id").count() == 1
        assert Anonymiser.objects.filter(field="run_name").count() == 1
        assert Anonymiser.objects.filter(identifier=output_sample_id_1).count() == 1
        assert Anonymiser.objects.filter(identifier=output_run_name_1).count() == 1

        # Identify sample_id from testsite_1
        response = self.client.post(
            self.endpoint("sample_id"),
            data={
                "value": test_record_1["sample_id"],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["identifier"], output_sample_id_1)

        # Identify run_name from testsite_1
        response = self.client.post(
            self.endpoint("run_name"),
            data={
                "value": test_record_1["run_name"],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["identifier"], output_run_name_1)

        # Create record from testsite_2
        test_record_2 = next(iter(generate_test_data(n=1)))
        test_record_2["site"] = self.extra_site.code
        response = self.client.post(
            reverse("project.testproject", kwargs={"code": "testproject"}),
            data=test_record_2,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        output_sample_id_2 = response.json()["data"]["sample_id"]
        output_run_name_2 = response.json()["data"]["run_name"]

        assert TestModel.objects.count() == 2
        assert Anonymiser.objects.count() == 4
        assert Anonymiser.objects.filter(site__code="testsite_2").count() == 2
        assert Anonymiser.objects.filter(field="sample_id").count() == 2
        assert Anonymiser.objects.filter(field="run_name").count() == 2
        assert Anonymiser.objects.filter(identifier=output_sample_id_2).count() == 1
        assert Anonymiser.objects.filter(identifier=output_run_name_2).count() == 1

        # Identify sample_id from testsite_2
        response = self.client.post(
            self.endpoint("sample_id"),
            data={
                "site": self.extra_site.code,
                "value": test_record_2["sample_id"],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["identifier"], output_sample_id_2)

        # Identify run_name from testsite_2
        response = self.client.post(
            self.endpoint("run_name"),
            data={
                "site": self.extra_site.code,
                "value": test_record_2["run_name"],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["identifier"], output_run_name_2)

    def test_same_value_same_site(self):
        """
        Test that the same value from the same site is assigned the same identifier.
        """

        iterator = iter(generate_test_data(n=2))
        test_record_1 = next(iterator)
        response = self.client.post(
            reverse("project.testproject", kwargs={"code": "testproject"}),
            data=test_record_1,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        output_sample_id_1 = response.json()["data"]["sample_id"]
        output_run_name_1 = response.json()["data"]["run_name"]

        test_record_2 = next(iterator)
        test_record_2["run_name"] = test_record_1["run_name"]
        response = self.client.post(
            reverse("project.testproject", kwargs={"code": "testproject"}),
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
            reverse("project.testproject", kwargs={"code": "testproject"}),
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
            reverse("project.testproject", kwargs={"code": "testproject"}),
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
