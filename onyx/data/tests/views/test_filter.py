from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase, generate_test_data
from ...models.projects.test import TestModel


# TODO:
# - Test summarise function
# - Test all OnyxTypes
# - Test effect of suppressing data


class TestFilterView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions and create a set of test records.
        """

        super().setUp()
        self.endpoint = reverse("data.project", kwargs={"code": "test"})
        self.user = self.setup_user(
            "testuser", roles=["is_staff"], groups=["test.test"]
        )
        for payload in generate_test_data():
            response = self.client.post(self.endpoint, data=payload)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def assertEqualClimbIDs(self, records, qs, allow_empty=False):
        """
        Assert that the ClimbIDs in the records match the ClimbIDs in the queryset.
        """

        record_values = sorted(record["climb_id"] for record in records)
        qs_values = sorted(qs.distinct().values_list("climb_id", flat=True))

        if not allow_empty:
            self.assertTrue(record_values)
            self.assertTrue(qs_values)

        self.assertEqual(
            record_values,
            qs_values,
        )

    def _test_filter(self, field, value, qs, lookup="", allow_empty=False):
        """
        Test filtering a field with a value and lookup.
        """

        response = self.client.get(
            self.endpoint, data={f"{field}__{lookup}" if lookup else field: value}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqualClimbIDs(response.json()["data"], qs, allow_empty=allow_empty)

    def test_basic(self):
        """
        Test basic retrieval of all records.
        """

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqualClimbIDs(
            response.json()["data"],
            TestModel.objects.all(),
        )

    def test_unknown_field(self):
        """
        Test that a filter with an unknown field fails.
        """

        response = self.client.get(self.endpoint, data={"hello": ":)"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_text(self):
        """
        Test filtering a text field.
        """

        for lookup, value, qs in [
            ("", "run-1", TestModel.objects.filter(run_name="run-1")),
            ("exact", "run-1", TestModel.objects.filter(run_name__exact="run-1")),
            ("ne", "run-1", TestModel.objects.filter(run_name__ne="run-1")),
            (
                "in",
                "run-1, run-2, run-3",
                TestModel.objects.filter(run_name__in=["run-1", "run-2", "run-3"]),
            ),
            ("contains", "run", TestModel.objects.filter(run_name__contains="run")),
            ("startswith", "run", TestModel.objects.filter(run_name__startswith="run")),
            ("endswith", "n-1", TestModel.objects.filter(run_name__endswith="n-1")),
            ("iexact", "RUN-1", TestModel.objects.filter(run_name__iexact="RUN-1")),
            ("icontains", "RUN", TestModel.objects.filter(run_name__icontains="RUN")),
            (
                "istartswith",
                "RUN",
                TestModel.objects.filter(run_name__istartswith="RUN"),
            ),
            ("iendswith", "N-1", TestModel.objects.filter(run_name__iendswith="N-1")),
            ("regex", "run-1", TestModel.objects.filter(run_name__regex="run-1")),
            ("iregex", "RUN-1", TestModel.objects.filter(run_name__iregex="RUN-1")),
            ("length", 5, TestModel.objects.filter(run_name__length=5)),
            (
                "length__in",
                "1, 3, 5",
                TestModel.objects.filter(run_name__length__in=[1, 3, 5]),
            ),
            (
                "length__range",
                "3, 5",
                TestModel.objects.filter(run_name__length__range=[3, 5]),
            ),
            ("", "", TestModel.objects.filter(run_name__isnull=True)),
            ("ne", "", TestModel.objects.exclude(run_name__isnull=True)),
            ("isnull", True, TestModel.objects.filter(run_name__isnull=True)),
            ("isnull", False, TestModel.objects.exclude(run_name__isnull=True)),
            ("isnull", True, TestModel.objects.filter(run_name="")),
            ("isnull", False, TestModel.objects.exclude(run_name="")),
        ]:
            self._test_filter(
                field="run_name",
                value=value,
                qs=qs,
                lookup=lookup,
                allow_empty=True,
            )

        # Test the isnull lookup against invalid true/false values
        for value in ["", " ", "invalid"]:
            response = self.client.get(self.endpoint, data={"run_name__isnull": value})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_choice(self):
        """
        Test filtering a choice field.
        """

        choice_1_values = ["eng", "ENG", "Eng", "enG", "eng ", " eng", " eng "]
        choice_2_values = [
            "wales",
            "WALES",
            "Wales",
            "wAleS",
            "wales ",
            " wales",
            " wales ",
        ]
        choice_values = choice_1_values + choice_2_values

        for lookup, value, qs in (
            [
                (l, x, TestModel.objects.filter(country=x.strip().lower()))
                for l in ["", "exact"]
                for x in choice_values
            ]
            + [
                ("ne", x, TestModel.objects.exclude(country=x.strip().lower()))
                for x in choice_values
            ]
            + [
                (
                    "in",
                    ", ".join(x),
                    TestModel.objects.filter(
                        country__in=[y.strip().lower() for y in x]
                    ),
                )
                for x in zip(choice_1_values, choice_2_values)
            ]
            + [
                ("", "", TestModel.objects.filter(country__isnull=True)),
                ("ne", "", TestModel.objects.exclude(country__isnull=True)),
                ("isnull", True, TestModel.objects.filter(country__isnull=True)),
                ("isnull", False, TestModel.objects.exclude(country__isnull=True)),
                ("isnull", True, TestModel.objects.filter(country="")),
                ("isnull", False, TestModel.objects.exclude(country="")),
            ]
        ):
            self._test_filter(
                field="country",
                value=value,
                qs=qs,
                lookup=lookup,
            )

        # Test the isnull lookup against invalid true/false values
        for value in ["", " ", "invalid"]:
            response = self.client.get(self.endpoint, data={"country__isnull": value})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test an incorrect choice
        response = self.client.get(self.endpoint, data={"country": "ing"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_integer(self):
        """
        Test filtering an integer field.
        """

        for lookup, value, qs in [
            ("", 1, TestModel.objects.filter(start=1)),
            ("exact", 1, TestModel.objects.filter(start__exact=1)),
            ("ne", 1, TestModel.objects.exclude(start=1)),
            ("in", "1, 2, 3", TestModel.objects.filter(start__in=[1, 2, 3])),
            ("lt", 3, TestModel.objects.filter(start__lt=3)),
            ("lte", 3, TestModel.objects.filter(start__lte=3)),
            ("gt", 2, TestModel.objects.filter(start__gt=2)),
            ("gte", 2, TestModel.objects.filter(start__gte=2)),
            ("range", "1, 3", TestModel.objects.filter(start__range=[1, 3])),
        ]:
            self._test_filter(
                field="start",
                value=value,
                qs=qs,
                lookup=lookup,
            )

    def test_decimal(self):
        """
        Test filtering a decimal field.
        """

        for lookup, value, qs in [
            ("", 1.1, TestModel.objects.filter(score=1.1)),
            ("exact", 1.1, TestModel.objects.filter(score__exact=1.1)),
            ("ne", 1.1, TestModel.objects.exclude(score=1.1)),
            (
                "in",
                "1.1, 2.2, 3.3",
                TestModel.objects.filter(score__in=[1.1, 2.2, 3.3]),
            ),
            ("lt", 3.3, TestModel.objects.filter(score__lt=3.3)),
            ("lte", 3.3, TestModel.objects.filter(score__lte=3.3)),
            ("gt", 4.4, TestModel.objects.filter(score__gt=4.4)),
            ("gte", 4.4, TestModel.objects.filter(score__gte=4.4)),
            ("range", "1.1, 9.9", TestModel.objects.filter(score__range=[1.1, 9.9])),
        ]:
            self._test_filter(
                field="score",
                value=value,
                qs=qs,
                lookup=lookup,
                allow_empty=True,
            )

    def test_yearmonth(self):
        """
        Test filtering a yearmonth field.
        """

        for lookup, value, qs in [
            (
                "",
                "2022-01",
                TestModel.objects.filter(collection_month="2022-01-01"),
            ),
            (
                "exact",
                "2022-01",
                TestModel.objects.filter(collection_month__exact="2022-01-01"),
            ),
            (
                "ne",
                "2022-01",
                TestModel.objects.exclude(collection_month="2022-01-01"),
            ),
            (
                "in",
                "2022-01, 2022-02, 2022-03",
                TestModel.objects.filter(
                    collection_month__in=["2022-01-01", "2022-02-01", "2022-03-01"]
                ),
            ),
            (
                "lt",
                "2022-03",
                TestModel.objects.filter(collection_month__lt="2022-03-01"),
            ),
            (
                "lte",
                "2022-03",
                TestModel.objects.filter(collection_month__lte="2022-03-01"),
            ),
            (
                "gt",
                "2022-02",
                TestModel.objects.filter(collection_month__gt="2022-02-01"),
            ),
            (
                "gte",
                "2022-02",
                TestModel.objects.filter(collection_month__gte="2022-02-01"),
            ),
            (
                "range",
                "2022-01, 2022-03",
                TestModel.objects.filter(
                    collection_month__range=["2022-01-01", "2022-03-01"]
                ),
            ),
            (
                "year",
                2022,
                TestModel.objects.filter(collection_month__year=2022),
            ),
            (
                "year__in",
                "2022, 2023",
                TestModel.objects.filter(collection_month__year__in=[2022, 2023]),
            ),
            (
                "year__range",
                "2022, 2023",
                TestModel.objects.filter(collection_month__year__range=[2022, 2023]),
            ),
        ]:
            self._test_filter(
                field="collection_month",
                value=value,
                lookup=lookup,
                qs=qs,
                allow_empty=True,
            )

    def test_date(self):
        """
        Test filtering a date field.
        """

        for lookup, value, qs in [
            (
                "",
                "2023-01-01",
                TestModel.objects.filter(submission_date="2023-01-01"),
            ),
            (
                "exact",
                "2023-01-01",
                TestModel.objects.filter(submission_date="2023-01-01"),
            ),
            (
                "ne",
                "2023-01-01",
                TestModel.objects.exclude(submission_date="2023-01-01"),
            ),
            (
                "in",
                "2023-01-01, 2023-01-02, 2023-01-03",
                TestModel.objects.filter(
                    submission_date__in=["2023-01-01", "2023-01-02", "2023-01-03"]
                ),
            ),
            (
                "lt",
                "2023-01-03",
                TestModel.objects.filter(submission_date__lt="2023-01-03"),
            ),
            (
                "lte",
                "2023-01-03",
                TestModel.objects.filter(submission_date__lte="2023-01-03"),
            ),
            (
                "gt",
                "2023-01-02",
                TestModel.objects.filter(submission_date__gt="2023-01-02"),
            ),
            (
                "gte",
                "2023-01-02",
                TestModel.objects.filter(submission_date__gte="2023-01-02"),
            ),
            (
                "range",
                "2023-01-01, 2023-06-03",
                TestModel.objects.filter(
                    submission_date__range=["2023-01-01", "2023-06-03"]
                ),
            ),
            (
                "year",
                2023,
                TestModel.objects.filter(submission_date__year=2023),
            ),
            (
                "year__in",
                "2023, 2024",
                TestModel.objects.filter(submission_date__year__in=[2023, 2024]),
            ),
            (
                "year__range",
                "2023, 2024",
                TestModel.objects.filter(submission_date__year__range=[2023, 2024]),
            ),
            (
                "iso_year",
                2023,
                TestModel.objects.filter(submission_date__iso_year=2023),
            ),
            (
                "iso_year__in",
                "2023, 2024",
                TestModel.objects.filter(submission_date__iso_year__in=[2023, 2024]),
            ),
            (
                "iso_year__range",
                "2023, 2024",
                TestModel.objects.filter(submission_date__iso_year__range=[2023, 2024]),
            ),
            (
                "week",
                32,
                TestModel.objects.filter(submission_date__week=32),
            ),
            (
                "week__in",
                "32, 33",
                TestModel.objects.filter(submission_date__week__in=[32, 33]),
            ),
            (
                "week__range",
                "10, 33",
                TestModel.objects.filter(submission_date__week__range=[10, 33]),
            ),
        ]:
            self._test_filter(
                field="submission_date",
                value=value,
                qs=qs,
                lookup=lookup,
                allow_empty=True,
            )

    def test_bool(self):
        """
        Test filtering a boolean field.
        """

        true_values = [True, 1, "1", "on", "true", "TRUE", "trUe", "t"]
        false_values = [False, 0, "0", "off", "false", "FALSE", "faLse", "f"]

        for lookup, value, qs in (
            [
                (l, x, TestModel.objects.filter(concern=True))
                for l in ["", "exact"]
                for x in true_values
            ]
            + [
                (l, x, TestModel.objects.filter(concern=False))
                for l in ["", "exact"]
                for x in false_values
            ]
            + [("ne", x, TestModel.objects.filter(concern=False)) for x in true_values]
            + [("ne", x, TestModel.objects.filter(concern=True)) for x in false_values]
            + [
                ("in", "True, False", TestModel.objects.all()),
            ]
        ):
            self._test_filter(
                field="concern",
                value=value,
                qs=qs,
                lookup=lookup,
            )

    def test_relation(self):
        """
        Test filtering a relation field.
        """

        response = self.client.get(self.endpoint, data={"records__isnull": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqualClimbIDs(
            response.json()["data"],
            TestModel.objects.filter(records__isnull=True),
        )

        response = self.client.get(self.endpoint, data={"records__isnull": False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqualClimbIDs(
            response.json()["data"],
            TestModel.objects.filter(records__isnull=False),
        )

    def test_relation_invalid_lookup(self):
        """
        Test filtering a relation field with an invalid lookup.
        """

        response = self.client.get(self.endpoint, data={"records": 1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
