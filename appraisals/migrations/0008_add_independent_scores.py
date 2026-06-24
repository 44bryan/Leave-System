from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appraisals', '0007_add_warning_sent'),
    ]

    operations = [
        # HR Manager independent scores
        migrations.AddField(
            model_name='appraisalrecord',
            name='hr_ind_pf_quality_of_work',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='hr_ind_pf_quantity_of_work',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='hr_ind_pf_knowledge_techniques',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='hr_ind_pf_ability_to_learn',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='hr_ind_aa_motivation',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='hr_ind_aa_attitude_colleagues',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='hr_ind_aa_relations_patients',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='hr_ind_aa_judgment_team',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='hr_ind_aa_punctuality',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='hr_ind_aa_presentation',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        # Admin Director independent scores
        migrations.AddField(
            model_name='appraisalrecord',
            name='dir_ind_pf_quality_of_work',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='dir_ind_pf_quantity_of_work',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='dir_ind_pf_knowledge_techniques',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='dir_ind_pf_ability_to_learn',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='dir_ind_aa_motivation',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='dir_ind_aa_attitude_colleagues',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='dir_ind_aa_relations_patients',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='dir_ind_aa_judgment_team',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='dir_ind_aa_punctuality',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='dir_ind_aa_presentation',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        # CEO independent scores
        migrations.AddField(
            model_name='appraisalrecord',
            name='ceo_ind_pf_quality_of_work',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='ceo_ind_pf_quantity_of_work',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='ceo_ind_pf_knowledge_techniques',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='ceo_ind_pf_ability_to_learn',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='ceo_ind_aa_motivation',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='ceo_ind_aa_attitude_colleagues',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='ceo_ind_aa_relations_patients',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='ceo_ind_aa_judgment_team',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='ceo_ind_aa_punctuality',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
        migrations.AddField(
            model_name='appraisalrecord',
            name='ceo_ind_aa_presentation',
            field=models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')]),
        ),
    ]
