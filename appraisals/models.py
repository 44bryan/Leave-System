from django.db import models
from django.contrib.auth.models import User
from accounts.models import Employee


TRIMESTER_CHOICES = [
    (1, 'Trimester 1 — November to February'),
    (2, 'Trimester 2 — March to June'),
    (3, 'Trimester 3 — July to October'),
]

MASTERY_CHOICES = [(i, str(i)) for i in range(1, 6)]


class AppraisalCycle(models.Model):
    year         = models.PositiveIntegerField()
    trimester    = models.PositiveSmallIntegerField(choices=TRIMESTER_CHOICES)
    title        = models.CharField(max_length=200, blank=True)
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                     related_name='appraisal_cycles')
    initiated_at      = models.DateTimeField(auto_now_add=True)
    employee_deadline = models.DateField(
        null=True, blank=True,
        help_text='Last day for employees to submit their appraisal section.'
    )
    is_distributed = models.BooleanField(default=False)
    distributed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('year', 'trimester')
        ordering = ['-year', '-trimester']

    def __str__(self):
        return self.title or f"Trim {self.trimester} — {self.year}"

    def get_trimester_dates(self):
        return {1: 'Nov – Feb', 2: 'Mar – Jun', 3: 'Jul – Oct'}.get(self.trimester, '')


class AppraisalRecord(models.Model):
    STATUS_EMPLOYEE  = 'employee'
    STATUS_COWORKER  = 'coworker'
    STATUS_UNIT_HEAD = 'unit_head'
    STATUS_MANAGER   = 'manager'
    STATUS_HR        = 'hr'
    STATUS_DIRECTOR  = 'director'
    STATUS_CEO       = 'ceo'
    STATUS_DONE      = 'done'

    STATUS_CHOICES = [
        (STATUS_EMPLOYEE,  'Awaiting Employee'),
        (STATUS_COWORKER,  'Awaiting Co-Worker'),
        (STATUS_UNIT_HEAD, 'Awaiting Unit Head / Supervisor'),
        (STATUS_MANAGER,   'Awaiting Line Manager'),
        (STATUS_HR,        'Awaiting HR'),
        (STATUS_DIRECTOR,  'Awaiting Admin Director'),
        (STATUS_CEO,       'Awaiting CEO'),
        (STATUS_DONE,      'Complete'),
    ]

    cycle    = models.ForeignKey(AppraisalCycle, on_delete=models.CASCADE, related_name='records')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='appraisals')
    status   = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_EMPLOYEE)

    # Employee — job info
    tasks_summary     = models.TextField(blank=True)
    tasks_assimilated = models.TextField(blank=True)

    # Appraisee self-rating — Performance Factors (1–5)
    pf_quality_of_work      = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    pf_quantity_of_work     = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    pf_knowledge_techniques = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    pf_ability_to_learn     = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)

    # Appraisee self-rating — Attitude & Aptitude Factors (1–5)
    aa_motivation          = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    aa_attitude_colleagues = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    aa_relations_patients  = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    aa_judgment_team       = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    aa_punctuality         = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    aa_presentation        = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)

    # Employee — goals, awards, comments
    goals_to_reach          = models.TextField(blank=True)
    award_employee_of_month = models.BooleanField(default=False)
    award_other             = models.CharField(max_length=200, blank=True)
    award_bonus_points      = models.PositiveSmallIntegerField(default=0)  # manually set by supervisor/director/CEO
    comment_on_self         = models.TextField(blank=True)
    comment_on_supervision  = models.TextField(blank=True)
    comment_on_org          = models.TextField(blank=True)
    employee_signed_at      = models.DateTimeField(null=True, blank=True)
    employee_sig_b64        = models.TextField(blank=True, default='')

    # Co-worker
    coworker_comment   = models.TextField(blank=True)
    coworker_signed_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='coworker_appraisals')
    coworker_signed_at = models.DateTimeField(null=True, blank=True)
    coworker_sig_b64   = models.TextField(blank=True, default='')

    # Unit Head / Supervisor
    unit_head_comment   = models.TextField(blank=True)
    unit_head_signed_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                             related_name='unit_head_appraisals')
    unit_head_signed_at = models.DateTimeField(null=True, blank=True)
    unit_head_sig_b64   = models.TextField(blank=True, default='')

    # Line Manager — Appraiser Rating (1–5) + comment
    mgr_pf_quality_of_work      = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    mgr_pf_quantity_of_work     = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    mgr_pf_knowledge_techniques = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    mgr_pf_ability_to_learn     = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    mgr_aa_motivation           = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    mgr_aa_attitude_colleagues  = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    mgr_aa_relations_patients   = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    mgr_aa_judgment_team        = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    mgr_aa_punctuality          = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    mgr_aa_presentation         = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    manager_comment   = models.TextField(blank=True)
    manager_signed_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='manager_appraisals')
    manager_signed_at = models.DateTimeField(null=True, blank=True)
    manager_sig_b64   = models.TextField(blank=True, default='')

    # HR
    hr_comment   = models.TextField(blank=True)
    hr_signed_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='hr_appraisals')
    hr_signed_at = models.DateTimeField(null=True, blank=True)
    hr_sig_b64   = models.TextField(blank=True, default='')

    # Admin Director
    director_comment   = models.TextField(blank=True)
    director_signed_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='director_appraisals')
    director_signed_at = models.DateTimeField(null=True, blank=True)
    director_sig_b64   = models.TextField(blank=True, default='')

    # CEO
    ceo_comment   = models.TextField(blank=True)
    ceo_signed_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='ceo_appraisals')
    ceo_signed_at = models.DateTimeField(null=True, blank=True)
    ceo_sig_b64   = models.TextField(blank=True, default='')

    # Score override — HR / Director / CEO can override the unit head's scores.
    # Original mgr_* values are kept so the PDF can show both.
    override_pf_quality_of_work      = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    override_pf_quantity_of_work     = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    override_pf_knowledge_techniques = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    override_pf_ability_to_learn     = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    override_aa_motivation           = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    override_aa_attitude_colleagues  = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    override_aa_relations_patients   = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    override_aa_judgment_team        = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    override_aa_punctuality          = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    override_aa_presentation         = models.PositiveSmallIntegerField(null=True, blank=True, choices=MASTERY_CHOICES)
    # Legacy "last modifier" — kept for the total table footnote
    score_override_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='score_overrides')
    score_override_at = models.DateTimeField(null=True, blank=True)
    # Per-role audit trail — tracks which role actually changed the scores
    score_modified_by_hr       = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                                    related_name='hr_score_mods')
    score_modified_at_hr       = models.DateTimeField(null=True, blank=True)
    score_modified_by_director = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                                    related_name='director_score_mods')
    score_modified_at_director = models.DateTimeField(null=True, blank=True)
    score_modified_by_ceo      = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                                    related_name='ceo_score_mods')
    score_modified_at_ceo      = models.DateTimeField(null=True, blank=True)
    # Per-role score snapshots — stores {fname: value} for each field that role actually changed.
    # Keys are the bare field names (e.g. 'pf_quality_of_work'). Null = role made no changes.
    hr_score_changes       = models.JSONField(null=True, blank=True, default=None)
    director_score_changes = models.JSONField(null=True, blank=True, default=None)
    ceo_score_changes      = models.JSONField(null=True, blank=True, default=None)

    # HR deadline override — HR can re-open an employee's section after the cycle deadline
    hr_unlocked      = models.BooleanField(default=False)
    hr_unlock_note   = models.CharField(max_length=300, blank=True)
    hr_unlocked_at   = models.DateTimeField(null=True, blank=True)
    hr_unlocked_by   = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name='unlocked_appraisals')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cycle', 'employee')
        ordering = ['employee__user__last_name', 'employee__user__first_name']

    def __str__(self):
        return f"{self.employee.get_full_name()} — {self.cycle}"

    def _final_score(self, fname):
        """Return override value if set, else the supervisor's (mgr_*) value."""
        v = getattr(self, f'override_{fname}', None)
        return v if v is not None else getattr(self, f'mgr_{fname}', None)

    _SCORE_FIELD_LABELS = [
        ('pf_quality_of_work',      'Quality of Work'),
        ('pf_quantity_of_work',     'Quantity of Work'),
        ('pf_knowledge_techniques', 'Knowledge of Techniques'),
        ('pf_ability_to_learn',     'Ability / Interest to Learn'),
        ('aa_motivation',           'Motivation and Initiative'),
        ('aa_attitude_colleagues',  'Attitude towards Colleagues'),
        ('aa_relations_patients',   'Relations with Patients'),
        ('aa_judgment_team',        'Judgment, Team Spirit & Discretion'),
        ('aa_punctuality',          'Punctuality, Attendance & Honesty'),
        ('aa_presentation',         'Personal Presentation'),
    ]

    def score_changes_display(self):
        """Return list of dicts for every field where any role modified the supervisor's score.
        Each dict: label, supervisor, hr, director, ceo, final — None means that role did not touch it."""
        hr_ch  = self.hr_score_changes or {}
        dir_ch = self.director_score_changes or {}
        ceo_ch = self.ceo_score_changes or {}
        rows = []
        for fname, label in self._SCORE_FIELD_LABELS:
            hr_v  = hr_ch.get(fname)
            dir_v = dir_ch.get(fname)
            ceo_v = ceo_ch.get(fname)
            if hr_v is None and dir_v is None and ceo_v is None:
                continue
            rows.append({
                'label':      label,
                'supervisor': getattr(self, f'mgr_{fname}'),
                'hr':         hr_v,
                'director':   dir_v,
                'ceo':        ceo_v,
                'final':      self._final_score(fname),
            })
        return rows

    @property
    def has_score_override(self):
        return self.score_override_by is not None

    @property
    def mgr_performance_score(self):
        """Original score given by the supervisor (unit head)."""
        scores = [s for s in [
            self.mgr_pf_quality_of_work, self.mgr_pf_quantity_of_work,
            self.mgr_pf_knowledge_techniques, self.mgr_pf_ability_to_learn,
        ] if s is not None]
        if len(scores) < 4:
            return None
        return round((sum(scores) / 20) * 12.5, 2)

    @property
    def mgr_attitude_score(self):
        """Original score given by the supervisor (unit head)."""
        scores = [s for s in [
            self.mgr_aa_motivation, self.mgr_aa_attitude_colleagues,
            self.mgr_aa_relations_patients, self.mgr_aa_judgment_team,
            self.mgr_aa_punctuality, self.mgr_aa_presentation,
        ] if s is not None]
        if len(scores) < 6:
            return None
        return round((sum(scores) / 30) * 7.5, 2)

    @property
    def final_performance_score(self):
        """Final score: override if HR/Director/CEO changed it, else supervisor's score."""
        scores = [self._final_score(f) for f in [
            'pf_quality_of_work', 'pf_quantity_of_work',
            'pf_knowledge_techniques', 'pf_ability_to_learn',
        ]]
        if any(v is None for v in scores):
            return None
        return round((sum(scores) / 20) * 12.5, 2)

    @property
    def final_attitude_score(self):
        """Final score: override if HR/Director/CEO changed it, else supervisor's score."""
        scores = [self._final_score(f) for f in [
            'aa_motivation', 'aa_attitude_colleagues', 'aa_relations_patients',
            'aa_judgment_team', 'aa_punctuality', 'aa_presentation',
        ]]
        if any(v is None for v in scores):
            return None
        return round((sum(scores) / 30) * 7.5, 2)

    def discipline_deductions(self):
        from discipline.models import DisciplineRecord
        from datetime import date
        import calendar
        year, trim = self.cycle.year, self.cycle.trimester
        if trim == 1:
            feb_last = calendar.monthrange(year, 2)[1]
            from_date, to_date = date(year - 1, 11, 1), date(year, 2, feb_last)
        elif trim == 2:
            from_date, to_date = date(year, 3, 1), date(year, 6, 30)
        else:
            from_date, to_date = date(year, 7, 1), date(year, 10, 31)
        records = DisciplineRecord.objects.filter(
            employee=self.employee,
            date_issued__range=(from_date, to_date),
        )
        counts = {'verbal_warning': 0, 'written_caution': 0,
                  'final_warning': 0, 'suspension': 0, 'dismissal': 0}
        for r in records:
            if r.action_type in counts:
                counts[r.action_type] += 1
        total = sum(counts.values())
        return {'counts': counts, 'total': total, 'deduction': -total}

    @property
    def award_bonus(self):
        return self.award_bonus_points

    @property
    def total_score(self):
        """Uses final scores (override if set, else supervisor original)."""
        pf = self.final_performance_score
        aa = self.final_attitude_score
        if pf is None or aa is None:
            return None
        return round(pf + aa + self.discipline_deductions()['deduction'] + self.award_bonus, 2)
