from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data, _test_record
from projects.testproject.models import TestModel


class TestGetView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions and create a test record.
        """

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
        Test retrieval of a record by CLIMB ID.
        """

        response = self.client.get(self.endpoint(self.climb_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        _test_record(
            self, response.json()["data"], TestModel.objects.get(climb_id=self.climb_id)
        )

    def test_include(self):
        """
        Test retrieval of a record by CLIMB ID with included fields.
        """

        response = self.client.get(
            self.endpoint(self.climb_id), data={"include": "climb_id"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"], {"climb_id": self.climb_id})

        response = self.client.get(
            self.endpoint(self.climb_id),
            data={"include": ["climb_id", "published_date"]},
        )
        record = TestModel.objects.get(climb_id=self.climb_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["data"],
            {
                "climb_id": record.climb_id,
                "published_date": (
                    record.published_date.strftime("%Y-%m-%d")
                    if record.published_date
                    else None
                ),
            },
        )

    def test_exclude(self):
        """
        Test retrieval of a record by CLIMB ID with excluded fields.
        """

        response = self.client.get(
            self.endpoint(self.climb_id), data={"exclude": "climb_id"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("climb_id", response.json()["data"])
        _test_record(
            self,
            response.json()["data"],
            TestModel.objects.get(climb_id=self.climb_id),
            created=True,
        )

        response = self.client.get(
            self.endpoint(self.climb_id),
            data={"exclude": ["climb_id", "published_date"]},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("climb_id", response.json()["data"])
        self.assertNotIn("published_date", response.json()["data"])
        _test_record(
            self,
            response.json()["data"],
            TestModel.objects.get(climb_id=self.climb_id),
            created=True,
        )

    def test_not_found(self):
        """
        Test failure to retrieve a record that does not exist.
        """

        response = self.client.get(
            self.endpoint(f"C-{self.climb_id.removeprefix('C-')[::-1]}")
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_suppressed_not_found(self):
        """
        Test failure to retrieve a record that has been suppressed.
        """

        instance = TestModel.objects.get(climb_id=self.climb_id)
        instance.is_suppressed = True
        instance.save()

        response = self.client.get(self.endpoint(self.climb_id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
