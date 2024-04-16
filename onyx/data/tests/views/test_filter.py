from django.db.models import Q
from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxDataTestCase
from projects.testproject.models import TestModel, TestModelRecord


class TestFilterView(OnyxDataTestCase):
    def setUp(self):
        """
        Create a user with the required permissions and create a set of test records.
        """

        super().setUp()
        self.endpoint = reverse(
            "projects.testproject", kwargs={"code": self.project.code}
        )

    def _test_filter(self, field, value, qs, lookup="", allow_empty=False):
        """
        Test filtering a field with a value and lookup.
        """

        response = self.client.get(
            self.endpoint, data={f"{field}__{lookup}" if lookup else field: value}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqualClimbIDs(response.json()["data"], qs)

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

    def test_suppressed(self):
        """
        Test that suppressed records are not returned.
        """

        pass  # TODO

    def test_include_exclude(self):
        """
        Test including and excluding fields on a filter.
        """

        pass  # TODO

    def test_include_exclude_bad_field(self):
        """
        Test that including/excluding with an invalid field fails.
        """

        # Cannot provide a lookup with an include/exclude field
        response = self.client.get(self.endpoint, data={"include": "run_name__in"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.get(self.endpoint, data={"exclude": "run_name__in"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # This field is unknown
        response = self.client.get(self.endpoint, data={"include": "hello"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.get(self.endpoint, data={"exclude": "hello"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_text(self):
        """
        Test filtering a text field.
        """

        for lookup, value, qs in [
            ("", "world", TestModel.objects.filter(text_option_1="world")),
            ("exact", "world", TestModel.objects.filter(text_option_1__exact="world")),
            ("ne", "world", TestModel.objects.exclude(text_option_1="world")),
            (
                "in",
                "hello, world, hey, ,",
                TestModel.objects.filter(
                    text_option_1__in=["hello", "world", "hey", ""]
                ),
            ),
            (
                "notin",
                "hello, world, hey, ,",
                TestModel.objects.exclude(
                    text_option_1__in=["hello", "world", "hey", ""]
                ),
            ),
            (
                "contains",
                "orl",
                TestModel.objects.filter(text_option_1__contains="orl"),
            ),
            (
                "startswith",
                "wor",
                TestModel.objects.filter(text_option_1__startswith="wor"),
            ),
            (
                "endswith",
                "rld",
                TestModel.objects.filter(text_option_1__endswith="rld"),
            ),
            (
                "iexact",
                "HELLO",
                TestModel.objects.filter(text_option_1__iexact="HELLO"),
            ),
            (
                "icontains",
                "ELL",
                TestModel.objects.filter(text_option_1__icontains="ELL"),
            ),
            (
                "istartswith",
                "HEL",
                TestModel.objects.filter(text_option_1__istartswith="HEL"),
            ),
            (
                "iendswith",
                "LLO",
                TestModel.objects.filter(text_option_1__iendswith="LLO"),
            ),
            ("length", 5, TestModel.objects.filter(text_option_1__length=5)),
            (
                "length__in",
                "1, 3, 5",
                TestModel.objects.filter(text_option_1__length__in=[1, 3, 5]),
            ),
            (
                "length__range",
                "3, 5",
                TestModel.objects.filter(text_option_1__length__range=[3, 5]),
            ),
            ("", "", TestModel.objects.filter(text_option_1__isnull=True)),
            ("ne", "", TestModel.objects.exclude(text_option_1__isnull=True)),
            ("isnull", True, TestModel.objects.filter(text_option_1__isnull=True)),
            ("isnull", False, TestModel.objects.exclude(text_option_1__isnull=True)),
            ("isnull", True, TestModel.objects.filter(text_option_1="")),
            ("isnull", False, TestModel.objects.exclude(text_option_1="")),
        ]:
            self._test_filter(
                field="text_option_1",
                value=value,
                qs=qs,
                lookup=lookup,
            )

        # Test the isnull lookup against invalid true/false values
        for value in ["", " ", "invalid"]:
            response = self.client.get(
                self.endpoint, data={"text_option_1__isnull": value}
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_choice(self):
        """
        Test filtering a choice field.
        """

        choice_1_values = ["", "eng", "ENG", "Eng", "enG", "eng ", " eng", " eng "]
        choice_2_values = [
            "wales",
            "WALES",
            "Wales",
            "wAleS",
            "wales ",
            " wales",
            " wales ",
            "",
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
                (
                    "notin",
                    ", ".join(x),
                    TestModel.objects.exclude(
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
            ("", 1, TestModel.objects.filter(tests=1)),
            ("exact", 1, TestModel.objects.filter(tests__exact=1)),
            ("ne", 1, TestModel.objects.exclude(tests=1)),
            (
                "in",
                "1, 2, ,",
                TestModel.objects.filter(Q(tests__in=[1, 2]) | Q(tests__isnull=True)),
            ),
            (
                "notin",
                "1, 2, ,",
                TestModel.objects.exclude(Q(tests__in=[1, 2]) | Q(tests__isnull=True)),
            ),
            ("lt", 3, TestModel.objects.filter(tests__lt=3)),
            ("lte", 3, TestModel.objects.filter(tests__lte=3)),
            ("gt", 2, TestModel.objects.filter(tests__gt=2)),
            ("gte", 2, TestModel.objects.filter(tests__gte=2)),
            ("range", "1, 3", TestModel.objects.filter(tests__range=[1, 3])),
            ("", "", TestModel.objects.filter(tests__isnull=True)),
            ("ne", "", TestModel.objects.exclude(tests__isnull=True)),
            ("isnull", True, TestModel.objects.filter(tests__isnull=True)),
            ("isnull", False, TestModel.objects.exclude(tests__isnull=True)),
        ]:
            self._test_filter(
                field="tests",
                value=value,
                qs=qs,
                lookup=lookup,
            )

        # Test the isnull lookup against invalid true/false values
        for value in ["", " ", "invalid"]:
            response = self.client.get(self.endpoint, data={"tests__isnull": value})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_decimal(self):
        """
        Test filtering a decimal field.
        """

        for lookup, value, qs in [
            ("", 1.12345, TestModel.objects.filter(score=1.12345)),
            ("exact", 1.12345, TestModel.objects.filter(score__exact=1.12345)),
            ("ne", 1.12345, TestModel.objects.exclude(score=1.12345)),
            (
                "in",
                "1.12345, 2.12345, 3.12345, ,",
                TestModel.objects.filter(
                    Q(score__in=[1.12345, 2.12345, 3.12345]) | Q(score__isnull=True)
                ),
            ),
            (
                "notin",
                "1.12345, 2.12345, 3.12345, ,",
                TestModel.objects.exclude(
                    Q(score__in=[1.12345, 2.12345, 3.12345]) | Q(score__isnull=True)
                ),
            ),
            ("lt", 3.12345, TestModel.objects.filter(score__lt=3.12345)),
            ("lte", 3.12345, TestModel.objects.filter(score__lte=3.12345)),
            ("gt", 4.12345, TestModel.objects.filter(score__gt=4.12345)),
            ("gte", 4.12345, TestModel.objects.filter(score__gte=4.12345)),
            (
                "range",
                "1.12345, 9.12345",
                TestModel.objects.filter(score__range=[1.12345, 9.12345]),
            ),
            ("", "", TestModel.objects.filter(score__isnull=True)),
            ("ne", "", TestModel.objects.exclude(score__isnull=True)),
            ("isnull", True, TestModel.objects.filter(score__isnull=True)),
            ("isnull", False, TestModel.objects.exclude(score__isnull=True)),
        ]:
            self._test_filter(
                field="score",
                value=value,
                qs=qs,
                lookup=lookup,
            )

        # Test the isnull lookup against invalid true/false values
        for value in ["", " ", "invalid"]:
            response = self.client.get(self.endpoint, data={"score__isnull": value})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
                "2022-01, 2022-03, ,",
                TestModel.objects.filter(
                    Q(collection_month__in=["2022-01-01", "2022-03-01"])
                    | Q(collection_month__isnull=True)
                ),
            ),
            (
                "notin",
                "2022-01, 2022-03, ,",
                TestModel.objects.exclude(
                    Q(collection_month__in=["2022-01-01", "2022-03-01"])
                    | Q(collection_month__isnull=True)
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
            ("", "", TestModel.objects.filter(collection_month__isnull=True)),
            ("ne", "", TestModel.objects.exclude(collection_month__isnull=True)),
            ("isnull", True, TestModel.objects.filter(collection_month__isnull=True)),
            ("isnull", False, TestModel.objects.exclude(collection_month__isnull=True)),
        ]:
            self._test_filter(
                field="collection_month",
                value=value,
                lookup=lookup,
                qs=qs,
            )

        # Test the isnull lookup against invalid true/false values
        for value in ["", " ", "invalid"]:
            response = self.client.get(
                self.endpoint, data={"collection_month__isnull": value}
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
                "2023-01-01, 2023-01-03, ,",
                TestModel.objects.filter(
                    Q(submission_date__in=["2023-01-01", "2023-01-03"])
                    | Q(submission_date__isnull=True)
                ),
            ),
            (
                "notin",
                "2023-01-01, 2023-01-03, ,",
                TestModel.objects.exclude(
                    Q(submission_date__in=["2023-01-01", "2023-01-03"])
                    | Q(submission_date__isnull=True)
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
            ("", "", TestModel.objects.filter(submission_date__isnull=True)),
            ("ne", "", TestModel.objects.exclude(submission_date__isnull=True)),
            ("isnull", True, TestModel.objects.filter(submission_date__isnull=True)),
            ("isnull", False, TestModel.objects.exclude(submission_date__isnull=True)),
        ]:
            self._test_filter(
                field="submission_date",
                value=value,
                qs=qs,
                lookup=lookup,
            )

        # Test the isnull lookup against invalid true/false values
        for value in ["", " ", "invalid"]:
            response = self.client.get(
                self.endpoint, data={"submission_date__isnull": value}
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
            + [("ne", x, TestModel.objects.exclude(concern=True)) for x in true_values]
            + [
                ("ne", x, TestModel.objects.exclude(concern=False))
                for x in false_values
            ]
            + [
                (
                    "in",
                    "True, ,",
                    TestModel.objects.filter(
                        Q(concern__in=[True]) | Q(concern__isnull=True)
                    ),
                ),
                (
                    "notin",
                    "True, ,",
                    TestModel.objects.exclude(
                        Q(concern__in=[True]) | Q(concern__isnull=True)
                    ),
                ),
                ("", "", TestModel.objects.filter(concern__isnull=True)),
                ("ne", "", TestModel.objects.exclude(concern__isnull=True)),
                (
                    "isnull",
                    True,
                    TestModel.objects.filter(concern__isnull=True),
                ),
                (
                    "isnull",
                    False,
                    TestModel.objects.exclude(concern__isnull=True),
                ),
            ]
        ):
            self._test_filter(
                field="concern",
                value=value,
                qs=qs,
                lookup=lookup,
            )

        # Test the isnull lookup against invalid true/false values
        for value in ["", " ", "invalid"]:
            response = self.client.get(self.endpoint, data={"concern__isnull": value})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_relation(self):
        """
        Test filtering a relation field.
        """

        for lookup, value, qs in [
            (
                "isnull",
                True,
                TestModel.objects.filter(records__isnull=True),
            ),
            (
                "isnull",
                False,
                TestModel.objects.filter(records__isnull=False),
            ),
        ]:
            self._test_filter(
                field="records",
                value=value,
                qs=qs,
                lookup=lookup,
            )

        # Test the isnull lookup against invalid true/false values
        for value in ["", " ", "invalid"]:
            response = self.client.get(self.endpoint, data={"records__isnull": value})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test filtering the relation field with an invalid lookup
        response = self.client.get(self.endpoint, data={"records": 1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_summarise(self):
        """
        Test filtering and summarising columns.
        """

        field_groups = [
            ("country",),
            ("run_name",),
            ("start",),
            ("score",),
            ("submission_date",),
            ("score", "required_when_published"),
            ("region", "run_name"),
            ("country", "concern"),
        ]

        for fields in field_groups:
            response = self.client.get(self.endpoint, data={"summarise": fields})
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Check that the number of distinct values in the response
            # matches the number of distinct values in the database
            self.assertEqual(
                len(response.json()["data"]),
                TestModel.objects.values(*fields).distinct().count(),
            )

            # Check that the counts match
            for row in response.json()["data"]:
                self.assertEqual(
                    row["count"],
                    TestModel.objects.filter(
                        **{field: row[field] for field in fields}
                    ).count(),
                )

        for fields in field_groups:
            response = self.client.get(
                self.endpoint, data={"summarise": fields, "country": "eng"}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Check that the number of distinct values in the response
            # matches the number of distinct values in the database
            self.assertEqual(
                len(response.json()["data"]),
                TestModel.objects.filter(country="eng")
                .values(*fields)
                .distinct()
                .count(),
            )

            # Check that the counts match
            for row in response.json()["data"]:
                self.assertEqual(
                    row["count"],
                    TestModel.objects.filter(country="eng")
                    .filter(**{field: row[field] for field in fields})
                    .count(),
                )

    def test_nested_summarise(self):
        """
        Test filtering and summarising nested columns.
        """

        nested_field_groups = [
            ("records__test_pass",),
            # TODO: Nested date fields cannot be summarised.
            # No current prod instances thankfully, but needs fixing ASAP
            # "records__test_start",
            ("records__test_result",),
            ("records__score_a",),
            ("records__score_c",),
            ("records__test_pass", "records__test_result"),
            ("records__score_b", "records__score_c", "records__test_pass"),
        ]

        for nested_fields in nested_field_groups:
            response = self.client.get(
                self.endpoint,
                data={"summarise": nested_fields},
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Check that the number of distinct values in the response
            # matches the number of distinct values in the database
            self.assertEqual(
                len(response.json()["data"]),
                TestModel.objects.filter(records__isnull=False)
                .values(*nested_fields)
                .distinct()
                .count(),
            )

            # Check that the counts match
            for row in response.json()["data"]:
                self.assertEqual(
                    row["records__count"],
                    TestModelRecord.objects.filter(
                        **{
                            nested_field.removeprefix("records__"): row[nested_field]
                            for nested_field in nested_fields
                        }
                    ).count(),
                )

        for nested_fields in nested_field_groups:
            response = self.client.get(
                self.endpoint,
                data={
                    "summarise": nested_fields,
                    "records__test_result": "details",
                },
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Check that the number of distinct values in the response
            # matches the number of distinct values in the database
            self.assertEqual(
                len(response.json()["data"]),
                TestModel.objects.filter(records__isnull=False)
                .filter(records__test_result="details")
                .values(*nested_fields)
                .distinct()
                .count(),
            )

            # Check that the counts match
            for row in response.json()["data"]:
                self.assertEqual(
                    row["records__count"],
                    TestModelRecord.objects.filter(test_result="details")
                    .filter(
                        **{
                            nested_field.removeprefix("records__"): row[nested_field]
                            for nested_field in nested_fields
                        }
                    )
                    .count(),
                )

    def test_mixed_summarise(self):
        """
        Test filtering and summarising a mix of columns and nested columns.
        """

        mixed_field_groups = [
            (
                ("run_name",),
                ("records__test_pass", "records__test_result"),
            ),
            (
                ("concern", "text_option_1"),
                ("records__score_a",),
            ),
        ]

        for fields, nested_fields in mixed_field_groups:
            response = self.client.get(
                self.endpoint,
                data={"summarise": fields + nested_fields},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Check that the number of distinct values in the response
            # matches the number of distinct values in the database
            self.assertEqual(
                len(response.json()["data"]),
                TestModel.objects.filter(records__isnull=False)
                .values(*(fields + nested_fields))
                .distinct()
                .count(),
            )

            # Check that the counts match
            for row in response.json()["data"]:
                self.assertEqual(
                    row["records__count"],
                    TestModelRecord.objects.filter(
                        **{
                            nested_field.removeprefix("records__"): row[nested_field]
                            for nested_field in nested_fields
                        }
                        | {f"link__{field}": row[field] for field in fields}
                    ).count(),
                )

        for fields, nested_fields in mixed_field_groups:
            response = self.client.get(
                self.endpoint,
                data={
                    "summarise": fields + nested_fields,
                    "country": "eng",
                    "records__test_result": "details",
                },
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Check that the number of distinct values in the response
            # matches the number of distinct values in the database
            self.assertEqual(
                len(response.json()["data"]),
                TestModel.objects.filter(records__isnull=False)
                .filter(country="eng")
                .filter(records__test_result="details")
                .values(*(fields + nested_fields))
                .distinct()
                .count(),
            )

            # Check that the counts match
            for row in response.json()["data"]:
                self.assertEqual(
                    row["records__count"],
                    TestModelRecord.objects.filter(link__country="eng")
                    .filter(test_result="details")
                    .filter(
                        **{
                            nested_field.removeprefix("records__"): row[nested_field]
                            for nested_field in nested_fields
                        }
                        | {f"link__{field}": row[field] for field in fields}
                    )
                    .count(),
                )

    def test_summarise_bad_field(self):
        """
        Test that summarising with an invalid field fails.
        """

        # Cannot provide a lookup with a summarise field
        response = self.client.get(self.endpoint, data={"summarise": "run_name__in"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Cannot summarise over a relational field
        response = self.client.get(self.endpoint, data={"summarise": "records"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # This field is unknown
        response = self.client.get(self.endpoint, data={"summarise": "hello"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
