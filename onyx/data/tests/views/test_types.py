from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase
from ...types import OnyxType


class TestTypesView(OnyxTestCase):
    def setUp(self):
        super().setUp()
        self.endpoint = reverse("projects.types")

    def test_basic(self):
        """
        Test retrieval of available types.
        """

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        types = [
            {
                "type": onyx_type.label,
                "description": onyx_type.description,
                "lookups": [lookup for lookup in onyx_type.lookups if lookup],
            }
            for onyx_type in OnyxType
        ]

        self.assertEqual(response.json()["data"], types)
