from operator import xor
from django.db.models import Q
from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxDataTestCase
from projects.testproject.models import TestModel


# TODO: Tests for query endpoint


class TestQueryView(OnyxDataTestCase):
    def setUp(self):
        """
        Create a user with the required permissions and create a set of test records.
        """

        super().setUp()
        self.endpoint = reverse(
            "projects.testproject.query", kwargs={"code": self.project.code}
        )

    def test_basic(self):
        """
        Test basic retrieval of all records.
        """

        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqualClimbIDs(
            response.json()["data"],
            TestModel.objects.all(),
        )

    def test_operators(self):
        """
        Test a mixture of operators in a query.
        """

        queries = [
            ({"collection_month": "2022-01"}, Q(collection_month="2022-01-01")),
            ({"received_month": "2023-05"}, Q(received_month="2023-05-01")),
            (
                {
                    "&": [
                        {"collection_month": "2022-01"},
                        {"received_month": "2023-05"},
                    ]
                },
                Q(collection_month="2022-01-01") & Q(received_month="2023-05-01"),
            ),
            (
                {
                    "|": [
                        {"collection_month": "2022-01"},
                        {"received_month": "2023-05"},
                    ]
                },
                Q(collection_month="2022-01-01") | Q(received_month="2023-05-01"),
            ),
            (
                {
                    "&": [
                        {"collection_month": "2022-01"},
                        {
                            "|": [
                                {"received_month": "2023-05"},
                                {"received_month": "2023-06"},
                            ]
                        },
                    ]
                },
                Q(collection_month="2022-01-01")
                & (Q(received_month="2023-05-01") | Q(received_month="2023-06-01")),
            ),
            (
                {
                    "|": [
                        {"collection_month": "2022-01"},
                        {
                            "&": [
                                {"received_month": "2023-05"},
                                {"received_month": "2023-06"},
                            ],
                        },
                    ]
                },
                Q(collection_month="2022-01-01")
                | (Q(received_month="2023-05-01") & Q(received_month="2023-06-01")),
            ),
            (
                {"~": {"collection_month": "2022-01"}},
                ~Q(collection_month="2022-01-01"),
            ),
            (
                {
                    "~": {
                        "&": [
                            {"collection_month": "2022-01"},
                            {"received_month": "2023-05"},
                        ]
                    }
                },
                ~(Q(collection_month="2022-01-01") & Q(received_month="2023-05-01")),
            ),
            (
                {
                    "~": {
                        "|": [
                            {"collection_month": "2022-01"},
                            {"received_month": "2023-05"},
                        ]
                    }
                },
                ~(Q(collection_month="2022-01-01") | Q(received_month="2023-05-01")),
            ),
            (
                {
                    "&": [
                        {"collection_month": "2022-01"},
                        {"~": {"received_month": "2023-05"}},
                    ]
                },
                Q(collection_month="2022-01-01") & ~Q(received_month="2023-05-01"),
            ),
            (
                {
                    "^": [
                        {"collection_month": "2022-01"},
                        {
                            "|": [
                                {"received_month": "2023-05"},
                                {"received_month": "2023-06"},
                                {"received_month": "2023-07"},
                            ]
                        },
                    ]
                },
                xor(
                    Q(collection_month="2022-01-01"),
                    (
                        Q(received_month="2023-05-01")
                        | Q(received_month="2023-06-01")
                        | Q(received_month="2023-07-01")
                    ),
                ),
            ),
        ]

        for query, expected in queries:
            response = self.client.post(self.endpoint, data=query)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqualClimbIDs(
                response.json()["data"], TestModel.objects.filter(expected)
            )
