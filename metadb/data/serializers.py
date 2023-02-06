from rest_framework import serializers
from internal.serializers import DynamicFieldsModelSerializer
from accounts.models import Site
from data.models import Record, Pathogen, Mpx
from utils import fieldserializers, choices
from utils.functions import (
    enforce_optional_value_groups_create,
    enforce_optional_value_groups_update,
    enforce_yearmonth_order_create,
    enforce_yearmonth_order_update,
    enforce_yearmonth_non_future,
)


class RecordSerializer(DynamicFieldsModelSerializer):
    site = serializers.SlugRelatedField(queryset=Site.objects.all(), slug_field="code")

    class Meta:
        model = Record
        fields = [
            "site",
            "cid",
            "published_date",
        ]


class PathogenSerializer(RecordSerializer):
    collection_month = fieldserializers.YearMonthField(required=False, allow_null=True)
    received_month = fieldserializers.YearMonthField()

    class Meta:
        model = Pathogen
        fields = RecordSerializer.Meta.fields + [
            "sample_id",
            "run_name",
            "collection_month",
            "received_month",
            "fasta_path",
            "bam_path",
        ]

    def validate(self, data):
        """
        Additional validation carried out on either object creation or update

        Update is indicated by the existence of a `self.instance`

        Creation is indicated by `self.instance = None`
        """
        model = self.Meta.model
        errors = {}

        if self.instance:
            enforce_optional_value_groups_update(
                errors=errors,
                instance=self.instance,
                data=data,
                groups=model.OPTIONAL_VALUE_GROUPS,
            )
            enforce_yearmonth_order_update(
                errors=errors,
                instance=self.instance,
                lower_yearmonth="collection_month",
                higher_yearmonth="received_month",
                data=data,
            )

        else:
            enforce_optional_value_groups_create(
                errors=errors,
                data=data,
                groups=model.OPTIONAL_VALUE_GROUPS,
            )
            enforce_yearmonth_order_create(
                errors=errors,
                lower_yearmonth="collection_month",
                higher_yearmonth="received_month",
                data=data,
            )

        if data.get("collection_month"):
            enforce_yearmonth_non_future(
                errors=errors,
                name="collection_month",
                value=data["collection_month"],
            )

        if data.get("received_month"):
            enforce_yearmonth_non_future(
                errors=errors,
                name="received_month",
                value=data["received_month"],
            )

        if errors:
            raise serializers.ValidationError(errors)

        return data


class MpxSerializer(PathogenSerializer):
    sample_type = fieldserializers.LowerChoiceField(
        choices=Mpx._meta.get_field("sample_type").choices,
        error_messages={"invalid_choice": f"options: {choices.SAMPLE_TYPE_CHOICES}"},
    )
    seq_platform = fieldserializers.LowerChoiceField(
        choices=Mpx._meta.get_field("seq_platform").choices,
        error_messages={"invalid_choice": f"options: {choices.SEQ_PLATFORM_CHOICES}"},
    )
    enrichment_method = fieldserializers.LowerChoiceField(
        choices=Mpx._meta.get_field("enrichment_method").choices,
        error_messages={
            "invalid_choice": f"options: {choices.ENRICHMENT_METHOD_CHOICES}"
        },
    )
    seq_strategy = fieldserializers.LowerChoiceField(
        choices=Mpx._meta.get_field("seq_strategy").choices,
        error_messages={"invalid_choice": f"options: {choices.SEQ_STRATEGY_CHOICES}"},
    )
    source_of_library = fieldserializers.LowerChoiceField(
        choices=Mpx._meta.get_field("source_of_library").choices,
        error_messages={
            "invalid_choice": f"options: {choices.SOURCE_OF_LIBRARY_CHOICES}"
        },
    )
    country = fieldserializers.LowerChoiceField(
        choices=Mpx._meta.get_field("country").choices,
        error_messages={"invalid_choice": f"options: {choices.COUNTRY_CHOICES}"},
    )
    run_layout = fieldserializers.LowerChoiceField(
        choices=Mpx._meta.get_field("run_layout").choices,
        error_messages={"invalid_choice": f"options: {choices.RUN_LAYOUT_CHOICES}"},
    )
    patient_ageband = fieldserializers.LowerChoiceField(
        choices=Mpx._meta.get_field("patient_ageband").choices,
        error_messages={
            "invalid_choice": f"options: {choices.PATIENT_AGEBAND_CHOICES}"
        },
        required=False,
        allow_null=True,
    )
    sample_site = fieldserializers.LowerChoiceField(
        choices=Mpx._meta.get_field("sample_site").choices,
        error_messages={"invalid_choice": f"options: {choices.SAMPLE_SITE_CHOICES}"},
        required=False,
        allow_null=True,
    )
    ukhsa_region = fieldserializers.LowerChoiceField(
        choices=Mpx._meta.get_field("ukhsa_region").choices,
        error_messages={"invalid_choice": f"options: {choices.UKHSA_REGION_CHOICES}"},
        required=False,
        allow_null=True,
    )
    travel_status = fieldserializers.LowerChoiceField(
        choices=Mpx._meta.get_field("travel_status").choices,
        error_messages={"invalid_choice": f"options: {choices.TRAVEL_STATUS_CHOICES}"},
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Mpx
        fields = PathogenSerializer.Meta.fields + [
            "sample_type",
            "seq_platform",
            "instrument_model",
            "enrichment_method",
            "seq_strategy",
            "source_of_library",
            "bioinfo_pipe_name",
            "bioinfo_pipe_version",
            "country",
            "run_layout",
            "patient_ageband",
            "patient_id",
            "sample_site",
            "ukhsa_region",
            "travel_status",
            "outer_postcode",
            "epi_cluster",
            "csv_template_version",
        ]


def get_serializer(model):
    """
    Function that returns the appropriate serializer for the given model.
    """
    return {
        Pathogen: PathogenSerializer,
        Mpx: MpxSerializer,
    }[model]
