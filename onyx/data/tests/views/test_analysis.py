import copy
from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase
from ...models import Analysis


default_payload = {
    "name": "Test Analysis",
    "analysis_date": "2024-01-01",
}


class TestCreateAnalysisView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user
        self.client.force_authenticate(self.admin_user)  # type: ignore

        self.endpoint = reverse(
            "projects.testproject.analysis", kwargs={"code": self.project.code}
        )

    def test_basic(self):
        """
        Test creating an analysis.
        """

        payload = copy.deepcopy(default_payload)
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert Analysis.objects.count() == 1


class TestGetAnalysisView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user to create the data
        self.client.force_authenticate(self.admin_user)  # type: ignore
        response = self.client.post(
            reverse(
                "projects.testproject.analysis", kwargs={"code": self.project.code}
            ),
            data=copy.deepcopy(default_payload),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.analysis_id = response.json()["data"]["analysis_id"]

        # Authenticate as the analyst user to retrieve the data
        self.client.force_authenticate(self.analyst_user)  # type: ignore

        self.endpoint = lambda analysis_id: reverse(
            "projects.testproject.analysis.analysis_id",
            kwargs={"code": self.project.code, "analysis_id": analysis_id},
        )

    def test_basic(self):
        """
        Test retrieval of an analysis by analysis ID.
        """

        response = self.client.get(self.endpoint(self.analysis_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_analysis_id_not_found(self):
        """
        Test retrieval of an analysis by analysis ID that does not exist.
        """

        prefix, postfix = self.analysis_id.split("-")
        analysis_id_not_found = "-".join([prefix, postfix[::-1]])
        response = self.client.get(self.endpoint(analysis_id_not_found))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestListAnalysisView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user to create the data
        self.client.force_authenticate(self.admin_user)  # type: ignore
        response = self.client.post(
            reverse(
                "projects.testproject.analysis", kwargs={"code": self.project.code}
            ),
            data=copy.deepcopy(default_payload),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Authenticate as the analyst user to retrieve the data
        self.client.force_authenticate(self.analyst_user)  # type: ignore

        self.endpoint = reverse(
            "projects.testproject.analysis", kwargs={"code": self.project.code}
        )

    def test_basic(self):
        """
        Test retrieval of all analyses.
        """

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 1)


class TestUpdateAnalysisView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user
        self.client.force_authenticate(self.admin_user)  # type: ignore
        self.endpoint = lambda analysis_id: reverse(
            "projects.testproject.analysis.analysis_id",
            kwargs={"code": self.project.code, "analysis_id": analysis_id},
        )

        response = self.client.post(
            reverse(
                "projects.testproject.analysis", kwargs={"code": self.project.code}
            ),
            data=copy.deepcopy(default_payload),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.analysis_id = response.json()["data"]["analysis_id"]

    def test_basic(self):
        """
        Test update of an analysis by analysis ID.
        """

        updated_values = {"name": "Updated Analysis Name"}
        response = self.client.patch(
            self.endpoint(self.analysis_id), data=updated_values
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_instance = Analysis.objects.get(analysis_id=self.analysis_id)
        self.assertEqual(updated_instance.name, updated_values["name"])

    def test_analysis_id_not_found(self):
        """
        Test update of an analysis by analysis ID that does not exist.
        """

        prefix, postfix = self.analysis_id.split("-")
        analysis_id_not_found = "-".join([prefix, postfix[::-1]])
        updated_values = {"name": "Updated Analysis Name"}
        response = self.client.patch(
            self.endpoint(analysis_id_not_found), data=updated_values
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Analysis.objects.filter(name=updated_values["name"]).exists())


class TestDeleteAnalysisView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user
        self.client.force_authenticate(self.admin_user)  # type: ignore
        self.endpoint = lambda analysis_id: reverse(
            "projects.testproject.analysis.analysis_id",
            kwargs={"code": self.project.code, "analysis_id": analysis_id},
        )

        response = self.client.post(
            reverse(
                "projects.testproject.analysis", kwargs={"code": self.project.code}
            ),
            data=copy.deepcopy(default_payload),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.analysis_id = response.json()["data"]["analysis_id"]

    def test_basic(self):
        """
        Test deletion of an analysis by analysis ID.
        """

        response = self.client.delete(self.endpoint(self.analysis_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Analysis.objects.filter(analysis_id=self.analysis_id).exists())

    def test_analysis_id_not_found(self):
        """
        Test deletion of an analysis by analysis ID that does not exist.
        """

        prefix, postfix = self.analysis_id.split("-")
        analysis_id_not_found = "-".join([prefix, postfix[::-1]])
        response = self.client.delete(self.endpoint(analysis_id_not_found))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Analysis.objects.filter(analysis_id=self.analysis_id).exists())
