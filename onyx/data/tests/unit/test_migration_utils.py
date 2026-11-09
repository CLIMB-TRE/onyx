from datetime import datetime, timezone
from ..utils import OnyxTestCase, generate_test_data
from data.migration_utils import backfill_published_timestamp
from projects.testproject.models import TestProject, HistoricalTestProject
from rest_framework import status
from rest_framework.reverse import reverse


class TestBackfillPublishedTimestamp(OnyxTestCase):
    def setUp(self):
        super().setUp()

        # Authenticate as the admin user
        self.client.force_authenticate(self.admin_user)  # type: ignore

        response = self.client.post(
            reverse("projects.testproject", kwargs={"code": self.project.code}),
            data=next(iter(generate_test_data(n=1))),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.instance = TestProject.objects.get(
            climb_id=response.json()["data"]["climb_id"]
        )

        # Simulate a legacy record: unpublish (so the constraint is not violated)
        # and clear the timestamp, bypassing save() and history
        TestProject.objects.filter(pk=self.instance.pk).update(
            is_published=False, published_timestamp=None
        )

    def test_from_history(self):
        """
        Test that the published timestamp is backfilled from the earliest
        historical record where the published date was set.
        """

        history_date = (
            HistoricalTestProject.objects.filter(
                id=self.instance.pk, published_date__isnull=False
            )
            .earliest("history_date")
            .history_date
        )

        backfill_published_timestamp(TestProject, HistoricalTestProject)
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.published_timestamp, history_date)

    def test_fallback(self):
        """
        Test that the published timestamp falls back to midnight UTC on the
        published date when there is no historical record to use.
        """

        HistoricalTestProject.objects.filter(id=self.instance.pk).delete()

        backfill_published_timestamp(TestProject, HistoricalTestProject)
        self.instance.refresh_from_db()
        assert self.instance.published_date is not None
        self.assertEqual(
            self.instance.published_timestamp,
            datetime.combine(
                self.instance.published_date,
                datetime.min.time(),
                tzinfo=timezone.utc,
            ),
        )
