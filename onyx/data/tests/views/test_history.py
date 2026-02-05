from datetime import timedelta, date
from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data
from ...exceptions import ClimbIDNotFound
from ...types import Actions, OnyxType
from projects.testproject.models import TestProject


class TestHistoryView(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user
        self.client.force_authenticate(self.admin_user)  # type: ignore

        self.endpoint = lambda climb_id: reverse(
            "projects.testproject.history.climb_id",
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
        Test getting the history of a record by CLIMB ID.
        """

        response = self.client.get(self.endpoint(self.climb_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["climb_id"], self.climb_id)
        self.assertEqual(len(response.json()["data"]["history"]), 1)
        self.assertEqual(
            response.json()["data"]["history"][0]["username"], self.admin_user.username
        )
        self.assertEqual(
            response.json()["data"]["history"][0]["action"], Actions.ADD.label
        )

    def test_climb_id_not_found(self):
        """
        Test getting the history of a record by CLIMB ID that does not exist.
        """

        prefix, postfix = self.climb_id.split("-")
        climb_id_not_found = "-".join([prefix, postfix[::-1]])
        response = self.client.get(self.endpoint(climb_id_not_found))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.json()["messages"]["detail"], ClimbIDNotFound.default_detail
        )

    def test_change_history(self):
        """
        Test getting the history of a record by CLIMB ID after an update.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        assert instance.submission_date is not None
        assert instance.tests is not None
        updated_values = {
            "submission_date": instance.submission_date + timedelta(days=1),
            "tests": instance.tests + 1,
            "text_option_2": instance.text_option_2 + "!",
        }
        response = self.client.patch(
            reverse(
                "projects.testproject.climb_id",
                kwargs={"code": self.project.code, "climb_id": self.climb_id},
            ),
            data=updated_values,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.endpoint(self.climb_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["climb_id"], self.climb_id)
        self.assertEqual(len(response.json()["data"]["history"]), 2)
        for diff in response.json()["data"]["history"]:
            self.assertEqual(diff["username"], self.admin_user.username)

        self.assertEqual(
            response.json()["data"]["history"][0]["action"], Actions.ADD.label
        )
        self.assertEqual(
            response.json()["data"]["history"][1]["action"], Actions.CHANGE.label
        )

        self.assertEqual(len(response.json()["data"]["history"][1]["changes"]), 3)
        types = {
            "submission_date": OnyxType.DATE.label,
            "tests": OnyxType.INTEGER.label,
            "text_option_2": OnyxType.TEXT.label,
        }
        for change in response.json()["data"]["history"][1]["changes"]:
            from_value = getattr(instance, change["field"])
            if isinstance(from_value, date):
                from_value = from_value.strftime("%Y-%m-%d")

            to_value = updated_values[change["field"]]
            if isinstance(to_value, date):
                to_value = to_value.strftime("%Y-%m-%d")

            self.assertEqual(change["type"], types[change["field"]])
            self.assertEqual(change["from"], from_value)
            self.assertEqual(change["to"], to_value)

    def test_nested_change_history(self):
        """
        Test getting the history of a record by CLIMB ID after an update with nested fields.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        assert instance.submission_date is not None
        assert instance.tests is not None
        updated_values = {
            "submission_date": instance.submission_date + timedelta(days=1),
            "tests": instance.tests + 1,
            "text_option_2": instance.text_option_2 + "!",
        }
        response = self.client.patch(
            reverse(
                "projects.testproject.climb_id",
                kwargs={"code": self.project.code, "climb_id": self.climb_id},
            ),
            data=updated_values,
        )
        updated_values = {
            "submission_date": instance.submission_date + timedelta(days=1),
            "tests": instance.tests + 1,
            "text_option_2": instance.text_option_2 + "!",
            "records": [
                {
                    "test_id": 1,
                    "test_result": "more_details",
                },
                {
                    "test_id": 2,
                    "test_result": "more_details",
                },
                {
                    "test_id": 1000,
                    "test_pass": True,
                    "test_start": "2024-01",
                    "test_end": "2024-01",
                    "score_a": 1,
                    "score_b": 1,
                    "test_result": "details",
                },
            ],
        }
        response = self.client.patch(
            reverse(
                "projects.testproject.climb_id",
                kwargs={"code": self.project.code, "climb_id": self.climb_id},
            ),
            data=updated_values,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(self.endpoint(self.climb_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["climb_id"], self.climb_id)
        self.assertEqual(len(response.json()["data"]["history"]), 3)
        for diff in response.json()["data"]["history"]:
            self.assertEqual(diff["username"], self.admin_user.username)

        self.assertEqual(
            response.json()["data"]["history"][0]["action"], Actions.ADD.label
        )
        self.assertEqual(
            response.json()["data"]["history"][1]["action"], Actions.CHANGE.label
        )
        self.assertEqual(
            response.json()["data"]["history"][2]["action"], Actions.CHANGE.label
        )

        self.assertEqual(len(response.json()["data"]["history"][1]["changes"]), 3)
        types = {
            "submission_date": OnyxType.DATE.label,
            "tests": OnyxType.INTEGER.label,
            "text_option_2": OnyxType.TEXT.label,
        }
        for change in response.json()["data"]["history"][1]["changes"]:
            from_value = getattr(instance, change["field"])
            if isinstance(from_value, date):
                from_value = from_value.strftime("%Y-%m-%d")

            to_value = updated_values[change["field"]]
            if isinstance(to_value, date):
                to_value = to_value.strftime("%Y-%m-%d")

            self.assertEqual(change["type"], types[change["field"]])
            self.assertEqual(change["from"], from_value)
            self.assertEqual(change["to"], to_value)

        self.assertEqual(len(response.json()["data"]["history"][2]["changes"]), 2)
        for change in response.json()["data"]["history"][2]["changes"]:
            self.assertEqual(change["field"], "records")
            self.assertEqual(change["type"], OnyxType.RELATION.label)

            if change["count"] == 1:
                self.assertEqual(change["action"], Actions.ADD.label)
            else:
                self.assertEqual(change["action"], Actions.CHANGE.label)
                self.assertEqual(change["count"], 2)

    def test_non_staff_different_site_hidden_change_values(self):
        """
        Test that the change values are hidden when the user is from a different site.
        """

        instance = TestProject.objects.get(climb_id=self.climb_id)
        assert instance.submission_date is not None
        assert instance.tests is not None
        updated_values = {
            "submission_date": instance.submission_date + timedelta(days=1),
            "tests": instance.tests + 1,
            "text_option_2": instance.text_option_2 + "!",
        }
        response = self.client.patch(
            reverse(
                "projects.testproject.climb_id",
                kwargs={"code": self.project.code, "climb_id": self.climb_id},
            ),
            data=updated_values,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        instance = TestProject.objects.get(climb_id=self.climb_id)
        instance.skip_history_when_saving = True  # type: ignore
        instance.site = self.extra_site
        instance.save()
        del instance.skip_history_when_saving  # type: ignore

        response = self.client.get(self.endpoint(self.climb_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["climb_id"], self.climb_id)
        self.assertEqual(len(response.json()["data"]["history"]), 2)
        for diff in response.json()["data"]["history"]:
            self.assertEqual(diff["username"], self.admin_user.username)

        self.assertEqual(
            response.json()["data"]["history"][0]["action"], Actions.ADD.label
        )
        self.assertEqual(
            response.json()["data"]["history"][1]["action"], Actions.CHANGE.label
        )

        self.assertEqual(len(response.json()["data"]["history"][1]["changes"]), 3)
        types = {
            "submission_date": OnyxType.DATE.label,
            "tests": OnyxType.INTEGER.label,
            "text_option_2": OnyxType.TEXT.label,
        }
        for change in response.json()["data"]["history"][1]["changes"]:
            self.assertEqual(change["type"], types[change["field"]])
            self.assertEqual(change["from"], "XXXX")
            self.assertEqual(change["to"], "XXXX")
