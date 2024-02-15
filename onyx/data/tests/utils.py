import os
import random
import logging
from django.core.management import call_command
from django.contrib.auth.models import Group
from rest_framework.test import APITestCase
from accounts.models import User, Site


directory = os.path.dirname(os.path.abspath(__file__))


class OnyxTestCase(APITestCase):
    def setUp(self):
        """
        Set up test case.
        """

        logging.disable(logging.CRITICAL)

        # Set up site and test project
        self.site = Site.objects.create(
            code="TEST",
            description="Department of Testing",
        )
        call_command(
            "project",
            os.path.join(directory, "project.json"),
            quiet=True,
        )

    def setup_user(self, username, roles=None, groups=None):
        """
        Create a user with the given username and roles/groups.
        """

        user, _ = User.objects.get_or_create(
            username=f"onyx-{username}", site=self.site
        )

        if roles:
            for role in roles:
                setattr(user, role, True)

        if groups:
            for group in groups:
                g = Group.objects.get(name=group)
                user.groups.add(g)

        self.client.force_authenticate(user)  # type: ignore
        return user


def generate_test_data(n: int = 100):
    """
    Generate test data.
    """

    # TODO: Better generation of test data
    # - Empty values for testing isnull without requiring allow_empty = True
    # - More distinct float, dates etc for testing exact filter matches without requiring allow_empty = True

    data = []
    for i in range(n):
        country_region_group = random.randint(0, 4)
        records = random.randint(0, 1)
        x = {
            "sample_id": f"sample-{i}",
            "run_name": f"run-{random.randint(1, 3)}",
            "collection_month": f"2022-{random.randint(1, 12)}",
            "received_month": f"2023-{random.randint(1, 6)}",
            "char_max_length_20": "X" * 20,
            "text_option_1": random.choice(["hi", ""]),
            "text_option_2": "bye",
            "submission_date": f"2023-{random.randint(1, 6)}-{random.randint(1, 25)}",
            "country": ["eng", "scot", "wales", "ni", ""][country_region_group],
            "region": [
                random.choice(["ne", "se", "nw", "sw", ""]),
                "other",
                "other",
                "other",
                "",
            ][country_region_group],
            "concern": random.choice([True, False]),
            "tests": 2,
            "score": random.random() * 42,
            "start": random.randint(1, 5),
            "end": random.randint(6, 10),
            "required_when_published": "hello",
        }
        if records:
            x["records"] = [
                {
                    "test_id": 1,
                    "test_pass": random.choice([True, False]),
                    "test_start": f"2022-{random.randint(1, 12)}",
                    "test_end": f"2023-{random.randint(1, 6)}",
                    "score_a": random.random() * 42,
                    "test_result": "details",
                },
                {
                    "test_id": 2,
                    "test_pass": random.choice([True, False]),
                    "test_start": f"2022-{random.randint(1, 12)}",
                    "test_end": f"2023-{random.randint(1, 6)}",
                    "score_b": random.random() * 42,
                    "test_result": "details",
                },
            ]
        data.append(x)
    return data


def _test_record(self, payload, instance, created: bool = False):
    """
    Test that a payload's values match an instance.
    """

    # Assert that the instance has the correct values as the payload
    if not created:
        self.assertEqual(payload.get("climb_id", ""), instance.climb_id)
        self.assertEqual(
            payload.get("published_date"),
            (
                instance.published_date.strftime("%Y-%m-%d")
                if instance.published_date
                else None
            ),
        )

    self.assertEqual(payload.get("sample_id", ""), instance.sample_id)
    self.assertEqual(payload.get("run_name", ""), instance.run_name)
    self.assertEqual(
        payload.get("collection_month"),
        (
            instance.collection_month.strftime("%Y-%m")
            if instance.collection_month
            else None
        ),
    )
    self.assertEqual(
        payload.get("received_month"),
        instance.received_month.strftime("%Y-%m") if instance.received_month else None,
    )
    self.assertEqual(payload.get("char_max_length_20", ""), instance.char_max_length_20)
    self.assertEqual(payload.get("text_option_1", ""), instance.text_option_1)
    self.assertEqual(payload.get("text_option_2", ""), instance.text_option_2)
    self.assertEqual(
        payload.get("submission_date"),
        (
            instance.submission_date.strftime("%Y-%m-%d")
            if instance.submission_date
            else None
        ),
    )
    self.assertEqual(payload.get("country", ""), instance.country)
    self.assertEqual(payload.get("region", ""), instance.region)
    self.assertEqual(payload.get("concern"), instance.concern)
    self.assertEqual(payload.get("tests"), instance.tests)
    self.assertEqual(payload.get("score"), instance.score)
    self.assertEqual(payload.get("start"), instance.start)
    self.assertEqual(payload.get("end"), instance.end)

    # If the payload has nested records, check the correctness of these
    if payload.get("records"):
        self.assertEqual(len(payload["records"]), instance.records.count())

        for subrecord in payload["records"]:
            subinstance = instance.records.get(test_id=subrecord.get("test_id"))
            self.assertEqual(subrecord.get("test_id"), subinstance.test_id)
            self.assertEqual(subrecord.get("test_pass"), subinstance.test_pass)
            self.assertEqual(
                subrecord.get("test_start"),
                (
                    subinstance.test_start.strftime("%Y-%m")
                    if subinstance.test_start
                    else None
                ),
            )
            self.assertEqual(
                subrecord.get("test_end"),
                (
                    subinstance.test_end.strftime("%Y-%m")
                    if subinstance.test_end
                    else None
                ),
            )
            self.assertEqual(subrecord.get("score_a"), subinstance.score_a)
            self.assertEqual(subrecord.get("score_b"), subinstance.score_b)
            self.assertEqual(subrecord.get("score_c"), subinstance.score_c)
