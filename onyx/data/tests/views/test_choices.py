from rest_framework import status
from rest_framework.reverse import reverse
from ..utils import OnyxTestCase


class TestChoicesView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions.
        """

        super().setUp()
        self.endpoint = lambda field: reverse(
            "projects.testproject.choices.field",
            kwargs={"code": self.project.code, "field": field},
        )

    def test_basic(self):
        """
        Test retrieval of choices for a choice field.
        """

        response = self.client.get(self.endpoint("country"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.json()["data"]), {"eng", "wales", "scot", "ni"})

    def test_unknown_field(self):
        """
        Test failure to retrieve choices for an unknown field.
        """

        response = self.client.get(self.endpoint("unknown"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_choice_field(self):
        """
        Test failure to retrieve choices for a non-choice field.
        """

        response = self.client.get(self.endpoint("sample_id"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["messages"]["detail"], "This field is not a choice field."
        )
