# Generated by Django 5.0.8 on 2025-02-11 12:09

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_initial"),
        ("data", "0013_analysis_historicalanalysis"),
        ("testproject", "0012_testmodel_analyses"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name="HistoricalTestModel",
            new_name="HistoricalTestProject",
        ),
        migrations.RenameModel(
            old_name="HistoricalTestModelRecord",
            new_name="HistoricalTestProjectRecord",
        ),
        migrations.RenameModel(
            old_name="TestModel",
            new_name="TestProject",
        ),
        migrations.RenameModel(
            old_name="TestModelRecord",
            new_name="TestProjectRecord",
        ),
        migrations.AlterModelOptions(
            name="historicaltestproject",
            options={
                "get_latest_by": ("history_date", "history_id"),
                "ordering": ("-history_date", "-history_id"),
                "verbose_name": "historical test project",
                "verbose_name_plural": "historical test projects",
            },
        ),
        migrations.AlterModelOptions(
            name="historicaltestprojectrecord",
            options={
                "get_latest_by": ("history_date", "history_id"),
                "ordering": ("-history_date", "-history_id"),
                "verbose_name": "historical test project record",
                "verbose_name_plural": "historical test project records",
            },
        ),
        migrations.RemoveConstraint(
            model_name="testproject",
            name="testproject_testmodel_sample__401e0b_ut",
        ),
        migrations.RemoveConstraint(
            model_name="testproject",
            name="testproject_testmodel_collect_a6369e_ovg",
        ),
        migrations.RemoveConstraint(
            model_name="testproject",
            name="testproject_testmodel_text_op_d4965a_ovg",
        ),
        migrations.RemoveConstraint(
            model_name="testproject",
            name="testproject_testmodel_collect_c39c65_ord",
        ),
        migrations.RemoveConstraint(
            model_name="testproject",
            name="testproject_testmodel_start_e_d47778_ord",
        ),
        migrations.RemoveConstraint(
            model_name="testproject",
            name="testproject_testmodel_collect_d74368_nf",
        ),
        migrations.RemoveConstraint(
            model_name="testproject",
            name="testproject_testmodel_region__97e2cd_cr",
        ),
        migrations.RemoveConstraint(
            model_name="testproject",
            name="testproject_testmodel_is_publ_975e9c_cvr",
        ),
        migrations.RemoveConstraint(
            model_name="testproject",
            name="testproject_testmodel_is_publ_16d558_cvr",
        ),
        migrations.RemoveConstraint(
            model_name="testprojectrecord",
            name="testproject_testmodelrecord_link_te_d335bd_ut",
        ),
        migrations.RemoveConstraint(
            model_name="testprojectrecord",
            name="testproject_testmodelrecord_score_a_469f82_ovg",
        ),
        migrations.RemoveConstraint(
            model_name="testprojectrecord",
            name="testproject_testmodelrecord_test_st_f445a4_ord",
        ),
        migrations.RemoveConstraint(
            model_name="testprojectrecord",
            name="testproject_testmodelrecord_score_c_578323_cr",
        ),
        migrations.RemoveConstraint(
            model_name="testprojectrecord",
            name="testproject_testmodelrecord_test_pa_35bc17_cvr",
        ),
        migrations.RenameIndex(
            model_name="testproject",
            new_name="testproject_created_85d4ad_idx",
            old_name="testproject_created_6899af_idx",
        ),
        migrations.RenameIndex(
            model_name="testproject",
            new_name="testproject_climb_i_353774_idx",
            old_name="testproject_climb_i_cdc763_idx",
        ),
        migrations.RenameIndex(
            model_name="testproject",
            new_name="testproject_is_publ_7e595e_idx",
            old_name="testproject_is_publ_fa963e_idx",
        ),
        migrations.RenameIndex(
            model_name="testproject",
            new_name="testproject_publish_548d0c_idx",
            old_name="testproject_publish_163a20_idx",
        ),
        migrations.RenameIndex(
            model_name="testproject",
            new_name="testproject_is_supp_8b5cda_idx",
            old_name="testproject_is_supp_6a5d87_idx",
        ),
        migrations.RenameIndex(
            model_name="testproject",
            new_name="testproject_site_id_087313_idx",
            old_name="testproject_site_id_125b38_idx",
        ),
        migrations.RenameIndex(
            model_name="testproject",
            new_name="testproject_is_site_9eb412_idx",
            old_name="testproject_is_site_0182e6_idx",
        ),
        migrations.RenameIndex(
            model_name="testproject",
            new_name="testproject_sample__2830c7_idx",
            old_name="testproject_sample__f02fdb_idx",
        ),
        migrations.RenameIndex(
            model_name="testproject",
            new_name="testproject_sample__7cc81f_idx",
            old_name="testproject_sample__d547e0_idx",
        ),
        migrations.RenameIndex(
            model_name="testproject",
            new_name="testproject_run_nam_48ac7d_idx",
            old_name="testproject_run_nam_f17891_idx",
        ),
        migrations.RenameIndex(
            model_name="testproject",
            new_name="testproject_collect_e0d25c_idx",
            old_name="testproject_collect_71ff32_idx",
        ),
        migrations.RenameIndex(
            model_name="testproject",
            new_name="testproject_receive_74cec9_idx",
            old_name="testproject_receive_3676a3_idx",
        ),
        migrations.RenameIndex(
            model_name="testprojectrecord",
            new_name="testproject_created_3259c2_idx",
            old_name="testproject_created_d106fb_idx",
        ),
        migrations.RenameIndex(
            model_name="testprojectrecord",
            new_name="testproject_link_id_dd6c27_idx",
            old_name="testproject_link_id_b0f35e_idx",
        ),
        migrations.RenameIndex(
            model_name="testprojectrecord",
            new_name="testproject_test_id_a14c9f_idx",
            old_name="testproject_test_id_811b7e_idx",
        ),
        migrations.RenameIndex(
            model_name="testprojectrecord",
            new_name="testproject_test_pa_186d5d_idx",
            old_name="testproject_test_pa_4e443f_idx",
        ),
        migrations.RenameIndex(
            model_name="testprojectrecord",
            new_name="testproject_test_st_4d5b21_idx",
            old_name="testproject_test_st_b8932c_idx",
        ),
        migrations.RenameIndex(
            model_name="testprojectrecord",
            new_name="testproject_test_en_0f2bf3_idx",
            old_name="testproject_test_en_7043b8_idx",
        ),
        migrations.RenameIndex(
            model_name="testprojectrecord",
            new_name="testproject_score_a_71a50c_idx",
            old_name="testproject_score_a_15c0e7_idx",
        ),
        migrations.RenameIndex(
            model_name="testprojectrecord",
            new_name="testproject_score_b_84714e_idx",
            old_name="testproject_score_b_2c31f9_idx",
        ),
        migrations.RenameIndex(
            model_name="testprojectrecord",
            new_name="testproject_score_c_b05cb1_idx",
            old_name="testproject_score_c_505230_idx",
        ),
        migrations.RenameIndex(
            model_name="testprojectrecord",
            new_name="testproject_test_re_08e6fa_idx",
            old_name="testproject_test_re_04dc62_idx",
        ),
        migrations.AddConstraint(
            model_name="testproject",
            constraint=models.UniqueConstraint(
                fields=("sample_id", "run_name"),
                name="testproject_testproject_sample__401e0b_ut",
            ),
        ),
        migrations.AddConstraint(
            model_name="testproject",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("collection_month__isnull", False),
                    ("received_month__isnull", False),
                    _connector="OR",
                ),
                name="testproject_testproject_collect_a6369e_ovg",
                violation_error_message="At least one of collection_month, received_month is required.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testproject",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("text_option_1__isnull", False),
                    ("text_option_2__isnull", False),
                    _connector="OR",
                ),
                name="testproject_testproject_text_op_d4965a_ovg",
                violation_error_message="At least one of text_option_1, text_option_2 is required.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testproject",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("collection_month__isnull", True),
                    ("received_month__isnull", True),
                    ("collection_month__lte", models.F("received_month")),
                    _connector="OR",
                ),
                name="testproject_testproject_collect_c39c65_ord",
                violation_error_message="The collection_month must be less than or equal to received_month.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testproject",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("start__isnull", True),
                    ("end__isnull", True),
                    ("start__lte", models.F("end")),
                    _connector="OR",
                ),
                name="testproject_testproject_start_e_d47778_ord",
                violation_error_message="The start must be less than or equal to end.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testproject",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(
                        ("collection_month__isnull", True),
                        ("collection_month__lte", models.F("last_modified")),
                        _connector="OR",
                    ),
                    models.Q(
                        ("received_month__isnull", True),
                        ("received_month__lte", models.F("last_modified")),
                        _connector="OR",
                    ),
                    models.Q(
                        ("submission_date__isnull", True),
                        ("submission_date__lte", models.F("last_modified")),
                        _connector="OR",
                    ),
                ),
                name="testproject_testproject_collect_d74368_nf",
                violation_error_message="At least one of collection_month, received_month, submission_date is from the future.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testproject",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("region__isnull", False), _negated=True),
                    ("country__isnull", False),
                    _connector="OR",
                ),
                name="testproject_testproject_region__97e2cd_cr",
                violation_error_message="Each of country are required in order to set region.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testproject",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("is_published", True), _negated=True),
                    ("published_date__isnull", False),
                    _connector="OR",
                ),
                name="testproject_testproject_is_publ_975e9c_cvr",
                violation_error_message="Each of published_date are required in order to set is_published to the value.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testproject",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("is_published", True), _negated=True),
                    ("required_when_published__isnull", False),
                    _connector="OR",
                ),
                name="testproject_testproject_is_publ_16d558_cvr",
                violation_error_message="Each of required_when_published are required in order to set is_published to the value.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testprojectrecord",
            constraint=models.UniqueConstraint(
                fields=("link", "test_id"),
                name="testproject_testprojectrecord_link_te_d335bd_ut",
            ),
        ),
        migrations.AddConstraint(
            model_name="testprojectrecord",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("score_a__isnull", False),
                    ("score_b__isnull", False),
                    _connector="OR",
                ),
                name="testproject_testprojectrecord_score_a_469f82_ovg",
                violation_error_message="At least one of score_a, score_b is required.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testprojectrecord",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("test_start__isnull", True),
                    ("test_end__isnull", True),
                    ("test_start__lte", models.F("test_end")),
                    _connector="OR",
                ),
                name="testproject_testprojectrecord_test_st_f445a4_ord",
                violation_error_message="The test_start must be less than or equal to test_end.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testprojectrecord",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("score_c__isnull", False), _negated=True),
                    models.Q(("score_a__isnull", False), ("score_b__isnull", False)),
                    _connector="OR",
                ),
                name="testproject_testprojectrecord_score_c_578323_cr",
                violation_error_message="Each of score_a, score_b are required in order to set score_c.",
            ),
        ),
        migrations.AddConstraint(
            model_name="testprojectrecord",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("test_pass", True), _negated=True),
                    ("test_result__isnull", False),
                    _connector="OR",
                ),
                name="testproject_testprojectrecord_test_pa_35bc17_cvr",
                violation_error_message="Each of test_result are required in order to set test_pass to the value.",
            ),
        ),
    ]
