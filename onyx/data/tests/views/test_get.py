from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data, _test_record
from ...models.projects.test import TestModel


class TestGetView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions and create a test record.
        """

        super().setUp()
        self.endpoint = lambda climb_id: reverse(
            "data.project.climb_id", kwargs={"code": "test", "climb_id": climb_id}
        )
        self.user = self.setup_user(
            "testuser", roles=["is_staff"], groups=["test.test"]
        )
        response = self.client.post(
            reverse("data.project", kwargs={"code": "test"}),
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["data"],
            {
                "climb_id": self.climb_id,
                "published_date": TestModel.objects.get(
                    climb_id=self.climb_id
                ).published_date.strftime("%Y-%m-%d"),
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
        instance.suppressed = True
        instance.save()

        response = self.client.get(self.endpoint(self.climb_id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
