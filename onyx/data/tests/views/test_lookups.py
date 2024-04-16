from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase
from ...types import OnyxLookup, OnyxType


class TestLookupsView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions.
        """

        super().setUp()
        self.endpoint = reverse("projects.lookups")

    def test_basic(self):
        """
        Test retrieval of available lookups.
        """

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lookups = [
            {
                "lookup": onyx_lookup.label,
                "description": onyx_lookup.description,
                "types": [
                    onyx_type.label
                    for onyx_type in OnyxType
                    if onyx_lookup.label in onyx_type.lookups
                ],
            }
            for onyx_lookup in OnyxLookup
        ]
        self.assertEqual(response.json()["data"], lookups)
