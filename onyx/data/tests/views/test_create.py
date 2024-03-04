import copy
from datetime import datetime, timedelta
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.serializers import BooleanField
from ..utils import OnyxTestCase, _test_record
from projects.testproject.models import TestModel, TestModelRecord


# TODO:
# - Required field tests (i.e. no None/"" values)
# - Investigate IntegerField/FloatField different handling of True/False
# - Test validators/constraints for nested fields
# - Test Anonymiser


default_payload = {
    "sample_id": "sample-1234",
    "run_name": "run-5678",
    "collection_month": "2023-01",
    "received_month": "2023-02",
    "char_max_length_20": "X" * 20,
    "text_option_1": "hi",
    "text_option_2": "bye",
    "submission_date": "2023-03-01",
    "country": "eng",
    "region": "nw",
    "concern": False,
    "tests": 2,
    "score": 42.832,
    "start": 1,
    "end": 2,
    "required_when_published": "hello",
    "records": [
        {
            "test_id": 1,
            "test_pass": True,
            "test_start": "2023-01",
            "test_end": "2023-02",
            "score_a": 42.101,
            "test_result": "details",
        },
        {
            "test_id": 2,
            "test_pass": False,
            "test_start": "2023-03",
            "test_end": "2023-04",
            "score_b": 45.010,
        },
    ],
}


class TestCreateView(OnyxTestCase):
    def setUp(self):
        """
        Create a user with the required permissions.
        """

        super().setUp()
        self.endpoint = reverse("project.testproject", kwargs={"code": "testproject"})
        self.user = self.setup_user(
            "testuser", roles=["is_staff"], groups=["testproject.admin"]
        )

    def test_basic(self):
        """
        Test creating a record.
        """

        payload = copy.deepcopy(default_payload)
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert TestModel.objects.count() == 1
        assert TestModelRecord.objects.count() == 2
        instance = TestModel.objects.get(climb_id=response.json()["data"]["climb_id"])
        payload["sample_id"] = response.json()["data"]["sample_id"]
        payload["run_name"] = response.json()["data"]["run_name"]
        _test_record(self, payload, instance, created=True)

    def test_basic_test(self):
        """
        Test the test creation of a record.
        """

        payload = copy.deepcopy(default_payload)
        response = self.client.post(
            reverse("project.testproject.test", kwargs={"code": "testproject"}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0
        self.assertEqual(response.json()["data"], {})

    def test_bad_request(self):
        """
        Test that an empty or badly structured payload fails.
        """

        for payload in [
            None,
            {},
            "",
            "hi",
            0,
            [],
            {"records": ""},
            {"records": "hi"},
            {"records": 0},
            {"records": {}},
            {"sample_id": []},
            {None: {}},
            {"records": [[[[[[[[]]]]]]]]},
        ]:
            response = self.client.post(self.endpoint, data=payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            assert TestModel.objects.count() == 0
            assert TestModelRecord.objects.count() == 0

    def test_optional_fields(self):
        """
        Test that a payload with optional fields works.
        """

        payload = copy.deepcopy(default_payload)
        payload.pop("collection_month")
        payload.pop("region")
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert TestModel.objects.count() == 1
        assert TestModelRecord.objects.count() == 2
        instance = TestModel.objects.get(climb_id=response.json()["data"]["climb_id"])
        payload["sample_id"] = response.json()["data"]["sample_id"]
        payload["run_name"] = response.json()["data"]["run_name"]
        _test_record(self, payload, instance, created=True)

    def test_unpermissioned_viewable_field(self):
        """
        Test that a payload with an unpermissioned viewable field fails.
        """

        payload = copy.deepcopy(default_payload)
        payload["climb_id"] = "helloooo"
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

    def test_unpermissioned_unviewable_field(self):
        """
        Test that a payload with an unpermissioned unviewable field fails.
        """

        payload = copy.deepcopy(default_payload)
        payload["is_suppressed"] = "helloooo"
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

    def test_unknown_fields(self):
        """
        Test that a payload with unknown fields fails.
        """

        payload = copy.deepcopy(default_payload)
        payload["hello"] = "hi"
        payload["goodbye"] = "bye"
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

    def test_required_fields(self):
        """
        Test that a payload with missing required fields fails.
        """

        payload = copy.deepcopy(default_payload)
        payload.pop("sample_id")
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

    def test_nested_required_fields(self):
        """
        Test that a payload with missing required nested fields fails.
        """

        payload = copy.deepcopy(default_payload)
        payload["records"][0].pop("test_id")
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

    def test_conditional_required_fields(self):
        """
        Test that a payload with missing conditionally required fields fails.
        """

        payload = copy.deepcopy(default_payload)
        payload.pop("country")
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

    def test_nested_conditional_required_fields(self):
        """
        Test that a nested conditional required constraint works.
        """

        # We do not have all requirements for score_c
        # score_c requires score_a and score_b
        payload = copy.deepcopy(default_payload)
        payload["records"][0]["score_c"] = 42.3
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

        # We have all requirements for score_c
        payload = copy.deepcopy(default_payload)
        payload["records"][0]["score_a"] = 42.3
        payload["records"][0]["score_b"] = 42.3112
        payload["records"][0]["score_c"] = 42.4242
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert TestModel.objects.count() == 1
        assert TestModelRecord.objects.count() == 2
        instance = TestModel.objects.get(climb_id=response.json()["data"]["climb_id"])
        payload["sample_id"] = response.json()["data"]["sample_id"]
        payload["run_name"] = response.json()["data"]["run_name"]
        _test_record(self, payload, instance, created=True)

    def test_conditional_value_required_fields(self):
        """
        Test that a payload with missing conditional-value required fields fails.
        """

        payload = copy.deepcopy(default_payload)

        # required_when_published is required when the record is being published
        payload.pop("required_when_published")
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

        # required_when_published is not required when the record is not published
        payload["is_published"] = False
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert TestModel.objects.count() == 1
        assert TestModelRecord.objects.count() == 2
        instance = TestModel.objects.get(climb_id=response.json()["data"]["climb_id"])
        payload["sample_id"] = response.json()["data"]["sample_id"]
        payload["run_name"] = response.json()["data"]["run_name"]
        _test_record(self, payload, instance, created=True)

    def test_nested_conditional_value_required_fields(self):
        """
        Test that a nested conditional-value required constraint works.
        """

        payload = copy.deepcopy(default_payload)

        # test_result is required when its test_pass is True
        payload["records"][0].pop("test_result")
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

        # test_result is not required when its test_pass is False
        payload["records"][0]["test_pass"] = False
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert TestModel.objects.count() == 1
        assert TestModelRecord.objects.count() == 2
        instance = TestModel.objects.get(climb_id=response.json()["data"]["climb_id"])
        payload["sample_id"] = response.json()["data"]["sample_id"]
        payload["run_name"] = response.json()["data"]["run_name"]
        _test_record(self, payload, instance, created=True)

    def test_unique_together(self):
        """
        Test that a unique together constraint works.
        """

        payload = copy.deepcopy(default_payload)
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert TestModel.objects.count() == 1
        assert TestModelRecord.objects.count() == 2
        instance = TestModel.objects.get(climb_id=response.json()["data"]["climb_id"])
        payload["sample_id"] = response.json()["data"]["sample_id"]
        default_sample_id_identifier = payload["sample_id"]
        payload["run_name"] = response.json()["data"]["run_name"]
        default_run_name_identifier = payload["run_name"]
        _test_record(self, payload, instance, created=True)

        payload = copy.deepcopy(default_payload)
        payload["sample_id"] = "sample-2345"
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert TestModel.objects.count() == 2
        assert TestModelRecord.objects.count() == 4
        instance = TestModel.objects.get(climb_id=response.json()["data"]["climb_id"])
        payload["sample_id"] = response.json()["data"]["sample_id"]
        payload["run_name"] = response.json()["data"]["run_name"]
        _test_record(self, payload, instance, created=True)

        payload = copy.deepcopy(default_payload)
        payload["run_name"] = "run-2"
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        assert TestModel.objects.count() == 3
        assert TestModelRecord.objects.count() == 6
        instance = TestModel.objects.get(climb_id=response.json()["data"]["climb_id"])
        payload["sample_id"] = response.json()["data"]["sample_id"]
        payload["run_name"] = response.json()["data"]["run_name"]
        _test_record(self, payload, instance, created=True)

        payload = copy.deepcopy(default_payload)
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 3
        assert TestModelRecord.objects.count() == 6
        assert (
            TestModel.objects.filter(sample_id=default_sample_id_identifier).count()
            == 2
        )
        assert (
            TestModel.objects.filter(run_name=default_run_name_identifier).count() == 2
        )

    def test_nested_unique_together(self):
        """
        Test that a payload which violates a nested unique together constraint fails.
        """

        payload = copy.deepcopy(default_payload)
        payload["records"][0]["test_id"] = payload["records"][1]["test_id"]
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

    def test_optional_value_group(self):
        """
        Test that a payload which violates an optional value group constraint fails.
        """

        payload = copy.deepcopy(default_payload)
        payload.pop("collection_month")
        payload.pop("received_month")
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

        for op_1, op_2 in [
            ("collection_month", "received_month"),
            ("text_option_1", "text_option_2"),
        ]:
            for empty_value in [" ", "", None]:
                payload = copy.deepcopy(default_payload)
                payload[op_1] = empty_value
                payload[op_2] = empty_value
                response = self.client.post(self.endpoint, data=payload)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                assert TestModel.objects.count() == 0
                assert TestModelRecord.objects.count() == 0

    def test_nested_optional_value_group(self):
        """
        Test that a payload which violates a nested optional value group constraint fails.
        """

        payload = copy.deepcopy(default_payload)
        payload["records"][0].pop("score_a", None)
        payload["records"][0].pop("score_b", None)
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

    def test_ordering(self):
        """
        Test that a payload which violates an ordering constraint fails.
        """

        # Testing ordering with yearmonths
        payload = copy.deepcopy(default_payload)
        payload["collection_month"] = "2023-02"
        payload["received_month"] = "2023-01"
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

        # Testing ordering with integers
        payload = copy.deepcopy(default_payload)
        start = payload.pop("start")
        end = payload.pop("end")
        payload["end"] = start
        payload["start"] = end
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

    def test_nested_ordering(self):
        """
        Test that a payload which violates a nested ordering constraint fails.
        """

        payload = copy.deepcopy(default_payload)
        payload["records"][1]["test_start"] = "2023-04"
        payload["records"][1]["test_end"] = "2023-03"
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

    def test_choice_constraint(self):
        """
        Test that a payload which violates a choice constraint fails.
        """

        payload = copy.deepcopy(default_payload)
        payload["country"] = "wales"
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

        payload = copy.deepcopy(default_payload)
        payload["region"] = "other"
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

    def test_nested_choice_constraint(self):
        """
        Test that a payload which violates a nested choice constraint fails.
        """

        pass

    def test_future_constraint(self):
        """
        Test that a payload which violates a future constraint fails.
        """

        payload = copy.deepcopy(default_payload)
        payload["collection_month"] = (datetime.today() + timedelta(days=60)).strftime(
            "%Y-%m"
        )
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

        payload = copy.deepcopy(default_payload)
        payload["submission_date"] = (datetime.today() + timedelta(days=60)).strftime(
            "%Y-%m-%d"
        )
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

    def test_nested_future_constraint(self):
        """
        Test that a payload which violates a nested future constraint fails.
        """

        pass

    def test_charfield_too_long(self):
        """
        Test that a payload which violates a CharField length constraint fails.
        """

        payload = copy.deepcopy(default_payload)
        payload["char_max_length_20"] = "X" * 21
        response = self.client.post(self.endpoint, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assert TestModel.objects.count() == 0
        assert TestModelRecord.objects.count() == 0

    def test_text(self):
        """
        Test creating a text field.
        """

        good_texts = [
            ("hello", "hello"),
            ("  hello  ", "hello"),
            ("  ", ""),
            (0, "0"),
            (0.0, "0.0"),
        ]

        bad_texts = [
            True,
            False,
            None,
            [],
            {},
        ]

        for good_text, expected in good_texts:
            payload = copy.deepcopy(default_payload)
            payload["text_option_1"] = good_text
            response = self.client.post(self.endpoint, data=payload)
            payload["text_option_1"] = expected
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            assert TestModel.objects.count() == 1
            instance = TestModel.objects.get(
                climb_id=response.json()["data"]["climb_id"]
            )
            payload["sample_id"] = response.json()["data"]["sample_id"]
            payload["run_name"] = response.json()["data"]["run_name"]
            _test_record(self, payload, instance, created=True)
            TestModel.objects.all().delete()

        for bad_text in bad_texts:
            payload = copy.deepcopy(default_payload)
            payload["text_option_1"] = bad_text
            response = self.client.post(self.endpoint, data=payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            assert TestModel.objects.count() == 0
            assert TestModelRecord.objects.count() == 0

    def test_choice(self):
        """
        Test creating a choice field.
        """

        good_choices = [
            ("nW", "nw"),
            ("Nw", "nw"),
            ("NW", "nw"),
            (" nw", "nw"),
            ("    ", ""),
        ]

        bad_choices = [
            "not a choice",
            0,
            1,
            2.345,
            True,
            False,
            None,
            [],
            {},
        ]

        for good_choice, expected in good_choices:
            payload = copy.deepcopy(default_payload)
            payload["region"] = good_choice
            response = self.client.post(self.endpoint, data=payload)
            payload["region"] = expected
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            assert TestModel.objects.count() == 1
            instance = TestModel.objects.get(
                climb_id=response.json()["data"]["climb_id"]
            )
            payload["sample_id"] = response.json()["data"]["sample_id"]
            payload["run_name"] = response.json()["data"]["run_name"]
            _test_record(self, payload, instance, created=True)
            TestModel.objects.all().delete()

        for bad_choice in bad_choices:
            payload = copy.deepcopy(default_payload)
            payload["region"] = bad_choice
            response = self.client.post(self.endpoint, data=payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            assert TestModel.objects.count() == 0
            assert TestModelRecord.objects.count() == 0

    def test_int(self):
        """
        Test creating an integer field.
        """

        good_ints = [
            ("5", 5),
            ("  7  ", 7),
            ("1.", 1),
            (None, None),
        ]

        bad_ints = [
            "2.45",
            "hello",
            "",
            " ",
            2.345,
            True,
            False,
            [],
            {},
        ]

        for good_int, expected in good_ints:
            payload = copy.deepcopy(default_payload)
            payload["tests"] = good_int
            response = self.client.post(self.endpoint, data=payload)
            payload["tests"] = expected
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            assert TestModel.objects.count() == 1
            instance = TestModel.objects.get(
                climb_id=response.json()["data"]["climb_id"]
            )
            payload["sample_id"] = response.json()["data"]["sample_id"]
            payload["run_name"] = response.json()["data"]["run_name"]
            _test_record(self, payload, instance, created=True)
            TestModel.objects.all().delete()

        for bad_int in bad_ints:
            payload = copy.deepcopy(default_payload)
            payload["tests"] = bad_int
            response = self.client.post(self.endpoint, data=payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            assert TestModel.objects.count() == 0
            assert TestModelRecord.objects.count() == 0

    def test_float(self):
        """
        Test creating a decimal field.
        """

        good_floats = [
            ("42.832", 42.832),
            (" 55.873 ", 55.873),
            (True, 1.0),
            (False, 0.0),
            (None, None),
        ]

        bad_floats = [
            "2.45.3",
            "1/0",
            "goodbye",
            "",
            " ",
            [],
            {},
        ]

        for good_float, expected in good_floats:
            payload = copy.deepcopy(default_payload)
            payload["score"] = good_float
            response = self.client.post(self.endpoint, data=payload)
            payload["score"] = expected
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            assert TestModel.objects.count() == 1
            instance = TestModel.objects.get(
                climb_id=response.json()["data"]["climb_id"]
            )
            payload["sample_id"] = response.json()["data"]["sample_id"]
            payload["run_name"] = response.json()["data"]["run_name"]
            _test_record(self, payload, instance, created=True)
            TestModel.objects.all().delete()

        for bad_float in bad_floats:
            payload = copy.deepcopy(default_payload)
            payload["score"] = bad_float
            response = self.client.post(self.endpoint, data=payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            assert TestModel.objects.count() == 0
            assert TestModelRecord.objects.count() == 0

    def test_yearmonth(self):
        """
        Test creating a yearmonth field.
        """

        good_yearmonths = [
            ("2023-01", datetime(2023, 1, 1)),
            ("2022-12", datetime(2022, 12, 1)),
            (None, None),
        ]

        bad_yearmonths = [
            "0-0-0-0-",
            "0000-01",
            "209999999999-01",
            "2023-01-01",
            "2023-0",
            " 2023-01 ",
            "",
            " ",
            0,
            1,
            2.345,
            True,
            False,
            [],
            {},
        ]

        for good_yearmonth, expected in good_yearmonths:
            payload = copy.deepcopy(default_payload)
            payload["collection_month"] = good_yearmonth
            response = self.client.post(self.endpoint, data=payload)
            if expected is not None:
                payload["collection_month"] = expected.strftime("%Y-%m")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            assert TestModel.objects.count() == 1
            instance = TestModel.objects.get(
                climb_id=response.json()["data"]["climb_id"]
            )
            payload["sample_id"] = response.json()["data"]["sample_id"]
            payload["run_name"] = response.json()["data"]["run_name"]
            _test_record(self, payload, instance, created=True)
            TestModel.objects.all().delete()

        for bad_yearmonth in bad_yearmonths:
            payload = copy.deepcopy(default_payload)
            payload["collection_month"] = bad_yearmonth
            response = self.client.post(self.endpoint, data=payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            assert TestModel.objects.count() == 0
            assert TestModelRecord.objects.count() == 0

    def test_date(self):
        """
        Test creating a date field.
        """

        good_dates = [
            ("2023-01-01", datetime(2023, 1, 1)),
            ("2022-12-31", datetime(2022, 12, 31)),
            (None, None),
        ]

        bad_dates = [
            "0-0-0-0-",
            "0000-00-01",
            "209999999999-01-01",
            "2023-01",
            "2023-01-0",
            "",
            " ",
            0,
            1,
            2.345,
            True,
            False,
            [],
            {},
        ]

        for good_date, expected in good_dates:
            payload = copy.deepcopy(default_payload)
            payload["submission_date"] = good_date
            response = self.client.post(self.endpoint, data=payload)
            if expected is not None:
                payload["submission_date"] = expected.strftime("%Y-%m-%d")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            assert TestModel.objects.count() == 1
            instance = TestModel.objects.get(
                climb_id=response.json()["data"]["climb_id"]
            )
            payload["sample_id"] = response.json()["data"]["sample_id"]
            payload["run_name"] = response.json()["data"]["run_name"]
            _test_record(self, payload, instance, created=True)
            TestModel.objects.all().delete()

        for bad_date in bad_dates:
            payload = copy.deepcopy(default_payload)
            payload["submission_date"] = bad_date
            response = self.client.post(self.endpoint, data=payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            assert TestModel.objects.count() == 0
            assert TestModelRecord.objects.count() == 0

    def test_bool(self):
        """
        Test creating a boolean field.
        """

        good_bools = (
            [(value, True) for value in BooleanField.TRUE_VALUES]
            + [(value, False) for value in BooleanField.FALSE_VALUES]
            + [(value, None) for value in BooleanField.NULL_VALUES]
        )

        bad_bools = [
            "tRUE",
            "truE",
            " True ",
            "  False   ",
            "fALSE",
            "FalsE",
            " ",
            2.345,
            [],
            {},
        ]

        for good_bool, expected in good_bools:
            payload = copy.deepcopy(default_payload)
            payload["concern"] = good_bool
            response = self.client.post(self.endpoint, data=payload)
            payload["concern"] = expected
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            assert TestModel.objects.count() == 1
            instance = TestModel.objects.get(
                climb_id=response.json()["data"]["climb_id"]
            )
            payload["sample_id"] = response.json()["data"]["sample_id"]
            payload["run_name"] = response.json()["data"]["run_name"]
            _test_record(self, payload, instance, created=True)
            TestModel.objects.all().delete()

        for bad_bool in bad_bools:
            payload = copy.deepcopy(default_payload)
            payload["concern"] = bad_bool
            response = self.client.post(self.endpoint, data=payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            assert TestModel.objects.count() == 0
            assert TestModelRecord.objects.count() == 0
