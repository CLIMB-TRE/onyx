from rest_framework import serializers
from utils.validators import OnyxUniqueTogetherValidator
from utils.fieldserializers import DateField, ArrayField, StructureField
from data.serializers import BaseRecordSerializer, ProjectRecordSerializer
from .models import TestProject, TestProjectRecord


class TestProjectRecordSerializer(BaseRecordSerializer):
    test_start = DateField("%Y-%m", input_formats=["%Y-%m"])
    test_end = DateField("%Y-%m", input_formats=["%Y-%m"])

    class Meta:
        model = TestProjectRecord
        fields = BaseRecordSerializer.Meta.fields + [
            "test_id",
            "test_pass",
            "test_start",
            "test_end",
            "score_a",
            "score_b",
            "score_c",
            "test_result",
        ]

    class OnyxMeta(BaseRecordSerializer.OnyxMeta):
        identifiers = BaseRecordSerializer.OnyxMeta.identifiers + ["test_id"]
        orderings = BaseRecordSerializer.OnyxMeta.orderings + [
            ("test_start", "test_end"),
        ]
        optional_value_groups = BaseRecordSerializer.OnyxMeta.optional_value_groups + [
            ["score_a", "score_b"]
        ]
        conditional_required = BaseRecordSerializer.OnyxMeta.conditional_required | {
            "score_c": ["score_a", "score_b"]
        }
        conditional_value_required = (
            BaseRecordSerializer.OnyxMeta.conditional_value_required
            | {("test_pass", True, None): ["test_result"]}
        )


class TestProjectSerializer(ProjectRecordSerializer):
    collection_month = DateField(
        "%Y-%m",
        input_formats=["%Y-%m"],
        required=False,
        allow_null=True,
    )
    received_month = DateField(
        "%Y-%m",
        input_formats=["%Y-%m"],
        required=False,
        allow_null=True,
    )
    submission_date = DateField(
        "%Y-%m-%d",
        input_formats=["%Y-%m-%d"],
        required=False,
        allow_null=True,
    )
    scores = ArrayField(
        child=serializers.IntegerField(min_value=0), required=False, max_length=10
    )
    structure = StructureField(required=False)

    class Meta:
        model = TestProject
        fields = ProjectRecordSerializer.Meta.fields + [
            "sample_id",
            "run_name",
            "collection_month",
            "received_month",
            "char_max_length_20",
            "text_option_1",
            "text_option_2",
            "submission_date",
            "country",
            "region",
            "concern",
            "tests",
            "score",
            "start",
            "end",
            "required_when_published",
            "optional_when_published_1",
            "optional_when_published_2",
            "scores",
            "structure",
            "unique_together_1",
            "unique_together_2",
        ]
        validators = [
            OnyxUniqueTogetherValidator(
                queryset=TestProject.objects.all(),
                fields=["sample_id", "run_name"],
            ),
            OnyxUniqueTogetherValidator(
                queryset=TestProject.objects.all(),
                fields=["unique_together_1", "unique_together_2"],
            ),
        ]

    class OnyxMeta(ProjectRecordSerializer.OnyxMeta):
        relations = ProjectRecordSerializer.OnyxMeta.relations | {
            "records": TestProjectRecordSerializer,
        }
        relation_options = ProjectRecordSerializer.OnyxMeta.relation_options | {
            "records": {
                "many": True,
                "required": False,
            },
        }
        optional_value_groups = (
            ProjectRecordSerializer.OnyxMeta.optional_value_groups
            + [
                ["collection_month", "received_month"],
                ["text_option_1", "text_option_2"],
            ]
        )
        orderings = ProjectRecordSerializer.OnyxMeta.orderings + [
            ("collection_month", "received_month"),
            ("start", "end"),
        ]
        non_futures = ProjectRecordSerializer.OnyxMeta.non_futures + [
            "collection_month",
            "received_month",
            "submission_date",
        ]
        choice_constraints = ProjectRecordSerializer.OnyxMeta.choice_constraints + [
            ("country", "region")
        ]
        conditional_required = ProjectRecordSerializer.OnyxMeta.conditional_required | {
            "region": ["country"]
        }
        conditional_value_required = (
            ProjectRecordSerializer.OnyxMeta.conditional_value_required
            | {
                ("is_published", True, True): [
                    "required_when_published",
                ]
            }
        )
        conditional_value_optional_value_groups = (
            ProjectRecordSerializer.OnyxMeta.conditional_value_optional_value_groups
            | {
                ("is_published", True, True): [
                    "optional_when_published_1",
                    "optional_when_published_2",
                ]
            }
        )
        anonymised_fields = ProjectRecordSerializer.OnyxMeta.anonymised_fields | {
            "sample_id": "S-",
            "run_name": "R-",
        }
