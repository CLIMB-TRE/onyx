from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data
from projects.testproject.models import TestModel, TestModelRecord


# TODO: Tests for query endpoint


class TestQueryView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions and create a set of test records.
        """

        super().setUp()
        self.endpoint = reverse(
            "project.testproject.query", kwargs={"code": self.project.code}
        )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        for data in generate_test_data(n=100):
            nested_records = data.pop("records", [])
            data["site"] = cls.site
            data["user"] = cls.user

            if data.get("collection_month"):
                data["collection_month"] += "-01"

            if data.get("received_month"):
                data["received_month"] += "-01"

            record = TestModel.objects.create(**data)
            for nested_record in nested_records:
                nested_record["link"] = record
                nested_record["user"] = cls.user

                if nested_record.get("test_start"):
                    nested_record["test_start"] += "-01"

                if nested_record.get("test_end"):
                    nested_record["test_end"] += "-01"

                TestModelRecord.objects.create(**nested_record)
