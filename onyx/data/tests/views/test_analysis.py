import copy
import random
from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxDataTestCase
from ...models import Anonymiser, Analysis
from projects.testproject.models import TestProject


default_payload = {
    "name": "Test Analysis",
    "analysis_date": "2024-01-01",
    "pipeline_name": "Test Pipeline",
    "pipeline_version": "0.1.0",
    "result": "Test Result",
    "report": "s3://test-bucket/test-report.html",
    "testproject_records": [],
}


class OnyxAnalysisTestCase(OnyxDataTestCase):
    NUM_RECORDS = 10

    def setUp(self):
        super().setUp()

        self.CREATE = reverse(
            "projects.testproject.analysis",
            kwargs={"code": self.project.code},
        )

        self.TEST_CREATE = reverse(
            "projects.testproject.analysis.test",
            kwargs={"code": self.project.code},
        )

        self.GET = lambda analysis_id: reverse(
            "projects.testproject.analysis.analysis_id",
            kwargs={"code": self.project.code, "analysis_id": analysis_id},
        )

        self.FILTER = reverse(
            "projects.testproject.analysis",
            kwargs={"code": self.project.code},
        )

        self.UPDATE = lambda analysis_id: reverse(
            "projects.testproject.analysis.analysis_id",
            kwargs={"code": self.project.code, "analysis_id": analysis_id},
        )

        self.TEST_UPDATE = lambda analysis_id: reverse(
            "projects.testproject.analysis.test.analysis_id",
            kwargs={"code": self.project.code, "analysis_id": analysis_id},
        )

        self.DELETE = lambda analysis_id: reverse(
            "projects.testproject.analysis.analysis_id",
            kwargs={"code": self.project.code, "analysis_id": analysis_id},
        )

        self.HISTORY = lambda analysis_id: reverse(
            "projects.testproject.analysis.history.analysis_id",
            kwargs={"code": self.project.code, "analysis_id": analysis_id},
        )

        self.RECORD_ANALYSES = lambda climb_id: reverse(
            "projects.testproject.analyses.climb_id",
            kwargs={"code": self.project.code, "climb_id": climb_id},
        )

        self.ANALYSIS_RECORDS = lambda analysis_id: reverse(
            "projects.testproject.analysis.records.analysis_id",
            kwargs={"code": self.project.code, "analysis_id": analysis_id},
        )


class TestCreateAnalysisView(OnyxAnalysisTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user
        self.client.force_authenticate(self.admin_user)  # type: ignore

        # Create test identifier
        identifier = Anonymiser.objects.create(
            project=self.project,
            site=self.site,
            field="test_field",
            hash="test_hash",
            prefix="I-",
        )

        # Create a test payload
        self.payload = copy.deepcopy(default_payload)
        records = random.sample(list(TestProject.objects.all()), self.NUM_RECORDS // 2)
        self.payload["testproject_records"] = [record.climb_id for record in records]
        self.payload["identifiers"] = [identifier.identifier]

    def test_basic(self):
        """
        Test creating an analysis.
        """

        response = self.client.post(self.CREATE, data=self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert Analysis.objects.count() == 1
        self.assertEqual(
            response.json()["data"]["analysis_id"],
            Analysis.objects.get(name=self.payload["name"]).analysis_id,
        )

    def test_basic_test(self):
        """
        Test the test creation of an analysis.
        """

        response = self.client.post(self.TEST_CREATE, data=self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert Analysis.objects.count() == 0
        self.assertEqual(response.json()["data"], {})

    def test_upstream_downstream(self):
        """
        Test creating analyses with upstream and downstream analyses.
        """

        # Create the test payload and capture the analysis ID
        response = self.client.post(self.CREATE, data=self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert Analysis.objects.count() == 1
        analysis_id = response.json()["data"]["analysis_id"]

        # Create a new analysis with the analysis ID as an upstream analysis
        payload = copy.deepcopy(self.payload)
        payload["name"] += " #2"
        payload["upstream_analyses"] = [analysis_id]
        response = self.client.post(self.CREATE, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert Analysis.objects.count() == 2
        analysis_id_2 = response.json()["data"]["analysis_id"]

        # Create a new analysis with the analysis ID as a downstream analysis
        payload = copy.deepcopy(self.payload)
        payload["name"] += " #3"
        payload["upstream_analyses"] = [analysis_id_2]
        response = self.client.post(self.CREATE, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert Analysis.objects.count() == 3
        analysis_id_3 = response.json()["data"]["analysis_id"]

        # Check that the upstream and downstream analyses are set correctly
        analysis_1 = self.client.get(self.GET(analysis_id))
        analysis_2 = self.client.get(self.GET(analysis_id_2))
        analysis_3 = self.client.get(self.GET(analysis_id_3))
        self.assertEqual(
            analysis_1.json()["data"]["downstream_analyses"],
            [analysis_id_2],
        )
        self.assertEqual(
            analysis_2.json()["data"]["upstream_analyses"],
            [analysis_id],
        )
        self.assertEqual(
            analysis_2.json()["data"]["downstream_analyses"],
            [analysis_id_3],
        )
        self.assertEqual(
            analysis_3.json()["data"]["upstream_analyses"],
            [analysis_id_2],
        )

    def test_invalid_identifier(self):
        """
        Test creating an analysis with an invalid identifier.
        """

        # Create test identifier from the extra project
        # This is invalid because the identifier is from a different project
        identifier = Anonymiser.objects.create(
            project=self.extra_project,
            site=self.site,
            field="test_field",
            hash="test_hash",
            prefix="I-",
        )
        self.payload["identifiers"].append(identifier.identifier)
        response = self.client.post(self.TEST_CREATE, data=self.payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert Analysis.objects.count() == 0


class TestGetAnalysisView(OnyxAnalysisTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user to create the data
        self.client.force_authenticate(self.admin_user)  # type: ignore

        # Create a test payload
        response = self.client.post(self.CREATE, data=copy.deepcopy(default_payload))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.analysis_id = response.json()["data"]["analysis_id"]

        # Authenticate as the analyst user to retrieve the data
        self.client.force_authenticate(self.analyst_user)  # type: ignore

    def test_basic(self):
        """
        Test retrieval of an analysis by analysis ID.
        """

        response = self.client.get(self.GET(self.analysis_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_analysis_id_not_found(self):
        """
        Test retrieval of an analysis by analysis ID that does not exist.
        """

        prefix, postfix = self.analysis_id.split("-")
        analysis_id_not_found = "-".join([prefix, postfix[::-1]])
        response = self.client.get(self.GET(analysis_id_not_found))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestFilterAnalysisView(OnyxAnalysisTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user to create the data
        self.client.force_authenticate(self.admin_user)  # type: ignore

        # Create a test payload
        response = self.client.post(self.CREATE, data=copy.deepcopy(default_payload))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Authenticate as the analyst user to retrieve the data
        self.client.force_authenticate(self.analyst_user)  # type: ignore

    def test_basic(self):
        """
        Test retrieval of all analyses.
        """

        response = self.client.get(self.FILTER)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 1)


class TestUpdateAnalysisView(OnyxAnalysisTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user
        self.client.force_authenticate(self.admin_user)  # type: ignore

        # Create a test payload
        response = self.client.post(self.CREATE, data=copy.deepcopy(default_payload))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.analysis_id = response.json()["data"]["analysis_id"]

    def test_basic(self):
        """
        Test update of an analysis by analysis ID.
        """

        updated_values = {"name": "Updated Analysis Name"}
        response = self.client.patch(self.UPDATE(self.analysis_id), data=updated_values)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_instance = Analysis.objects.get(analysis_id=self.analysis_id)
        self.assertEqual(updated_instance.name, updated_values["name"])

    def test_basic_test(self):
        """
        Test the test update of an analysis by analysis ID.
        """

        instance = Analysis.objects.get(analysis_id=self.analysis_id)
        original_values = {
            "result": instance.result,
            "report": instance.report,
        }
        updated_values = {
            "result": instance.result + "!",
            "report": instance.report + "!",
        }
        response = self.client.patch(
            self.TEST_UPDATE(self.analysis_id), data=updated_values
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"], {})
        updated_instance = Analysis.objects.get(analysis_id=self.analysis_id)
        self.assertEqual(updated_instance.result, original_values["result"])
        self.assertEqual(updated_instance.report, original_values["report"])

    def test_analysis_id_not_found(self):
        """
        Test update of an analysis by analysis ID that does not exist.
        """

        prefix, postfix = self.analysis_id.split("-")
        analysis_id_not_found = "-".join([prefix, postfix[::-1]])
        updated_values = {"name": "Updated Analysis Name"}
        response = self.client.patch(
            self.UPDATE(analysis_id_not_found), data=updated_values
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Analysis.objects.filter(name=updated_values["name"]).exists())


class TestDeleteAnalysisView(OnyxAnalysisTestCase):
    # TODO: Analyses are currently un-deletable
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user
        self.client.force_authenticate(self.admin_user)  # type: ignore

        # Create a test payload
        response = self.client.post(self.CREATE, data=copy.deepcopy(default_payload))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.analysis_id = response.json()["data"]["analysis_id"]

    def test_basic(self):
        """
        Test deletion of an analysis by analysis ID.
        """

        response = self.client.delete(self.DELETE(self.analysis_id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # self.assertFalse(Analysis.objects.filter(analysis_id=self.analysis_id).exists())

    def test_analysis_id_not_found(self):
        """
        Test deletion of an analysis by analysis ID that does not exist.
        """

        prefix, postfix = self.analysis_id.split("-")
        analysis_id_not_found = "-".join([prefix, postfix[::-1]])
        response = self.client.delete(self.DELETE(analysis_id_not_found))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # self.assertTrue(Analysis.objects.filter(analysis_id=self.analysis_id).exists())


class TestAnalysisHistoryView(OnyxAnalysisTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user
        self.client.force_authenticate(self.admin_user)  # type: ignore

        # Create a test payload
        response = self.client.post(self.CREATE, data=copy.deepcopy(default_payload))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.analysis_id = response.json()["data"]["analysis_id"]

    def test_basic(self):
        """
        Test getting the history of an analysis by analysis ID.
        """

        response = self.client.get(self.HISTORY(self.analysis_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_analysis_id_not_found(self):
        """
        Test getting the history of an analysis by analysis ID that does not exist.
        """

        prefix, postfix = self.analysis_id.split("-")
        analysis_id_not_found = "-".join([prefix, postfix[::-1]])
        response = self.client.get(self.HISTORY(analysis_id_not_found))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestRecordAnalysesView(OnyxAnalysisTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user
        self.client.force_authenticate(self.admin_user)  # type: ignore

        # Get the target record CLIMB ID
        record = TestProject.objects.first()
        assert record is not None
        self.climb_id = record.climb_id

        # Create test payloads
        analysis_ids = []
        for i in range(self.NUM_RECORDS):
            payload = copy.deepcopy(default_payload)
            payload["name"] += f" #{i}"
            payload["testproject_records"] = [self.climb_id]
            response = self.client.post(self.CREATE, data=payload)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            analysis_ids.append(response.json()["data"]["analysis_id"])
        self.analysis_ids = set(analysis_ids)

    def test_basic(self):
        """
        Test getting the analyses of a record by CLIMB ID.
        """

        response = self.client.get(self.RECORD_ANALYSES(self.climb_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {analysis["analysis_id"] for analysis in response.json()["data"]},
            self.analysis_ids,
        )

    def test_climb_id_not_found(self):
        """
        Test getting the analyses of a record by CLIMB ID that does not exist.
        """

        prefix, postfix = self.climb_id.split("-")
        climb_id_not_found = "-".join([prefix, postfix[::-1]])
        response = self.client.get(self.RECORD_ANALYSES(climb_id_not_found))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestAnalysisRecordsView(OnyxAnalysisTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user
        self.client.force_authenticate(self.admin_user)  # type: ignore

        # Create a test payload
        self.payload = copy.deepcopy(default_payload)
        climb_ids = [
            record.climb_id
            for record in random.sample(
                list(TestProject.objects.all()), self.NUM_RECORDS // 2
            )
        ]
        self.payload["testproject_records"] = climb_ids
        self.climb_ids = set(climb_ids)
        response = self.client.post(self.CREATE, data=self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.analysis_id = response.json()["data"]["analysis_id"]

    def test_basic(self):
        """
        Test getting the records of an analysis by analysis ID.
        """

        response = self.client.get(self.ANALYSIS_RECORDS(self.analysis_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {record["climb_id"] for record in response.json()["data"]},
            self.climb_ids,
        )

    def test_analysis_id_not_found(self):
        """
        Test getting the records of an analysis by analysis ID that does not exist.
        """

        prefix, postfix = self.analysis_id.split("-")
        analysis_id_not_found = "-".join([prefix, postfix[::-1]])
        response = self.client.get(self.ANALYSIS_RECORDS(analysis_id_not_found))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
