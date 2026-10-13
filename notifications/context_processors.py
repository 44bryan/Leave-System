from datetime import date

def notifications_ctx(request):
    """Inject unread notification count, recent notifications, suspension status, and sidebar badge counts."""
    if not request.user.is_authenticated:
        return {}
    try:
        qs = request.user.system_notifications
        unread = qs.filter(is_read=False).count()
        recent = list(qs.all()[:6])

        is_suspended = False
        suspension_end = None
        pending_coworker_count = 0
        pending_leave_count = 0
        pending_medical_lm_count = 0
        pending_discipline_proposals = 0
        pending_consultations_count = 0
        # Per-page appraisal counts — each badge shows exactly what that page will show
        appraisal_self_count = 0
        appraisal_unit_head_count = 0
        appraisal_manager_count = 0
        appraisal_hr_count = 0
        appraisal_director_count = 0
        appraisal_ceo_count = 0

        try:
            emp = request.user.employee
            from discipline.models import DisciplineRecord
            from django.db.models import Q
            today = date.today()

            # Suspension check
            active_suspension = DisciplineRecord.objects.filter(
                employee=emp,
                action_type='suspension',
                is_proposal=False,
                suspension_start__lte=today,
                suspension_end__gte=today,
            ).order_by('-suspension_end').first()
            if active_suspension:
                is_suspended = True
                suspension_end = active_suspension.suspension_end

            # Appraisal counts — each matches exactly what the corresponding view page shows
            from appraisals.models import AppraisalRecord
            appraisal_self_count = AppraisalRecord.objects.filter(
                status=AppraisalRecord.STATUS_EMPLOYEE,
                employee=emp,
            ).count()
            pending_coworker_count = AppraisalRecord.objects.filter(
                coworker_signed_by=emp,
                status=AppraisalRecord.STATUS_COWORKER,
            ).count()
            # Unit head: same logic as pending_unit_head view
            appraisal_unit_head_count = AppraisalRecord.objects.filter(
                status=AppraisalRecord.STATUS_UNIT_HEAD,
            ).filter(
                Q(employee__unit_head=emp) |
                Q(employee__unit_head__isnull=True, employee__supervisor=emp)
            ).count()
            # Manager: same logic as pending_manager view
            appraisal_manager_count = AppraisalRecord.objects.filter(
                status=AppraisalRecord.STATUS_MANAGER,
                employee__supervisor=emp,
            ).count()
            if emp.is_hr():
                appraisal_hr_count = AppraisalRecord.objects.filter(
                    status=AppraisalRecord.STATUS_HR,
                ).count()
            if emp.is_director():
                appraisal_director_count = AppraisalRecord.objects.filter(
                    status=AppraisalRecord.STATUS_DIRECTOR,
                ).count()
            if emp.is_ceo():
                appraisal_ceo_count = AppraisalRecord.objects.filter(
                    status=AppraisalRecord.STATUS_CEO,
                ).count()

            # Leave queue badge — role-specific, matches exactly what the target view shows
            from leaves.models import LeaveRequest
            from django.urls import reverse
            pending_leave_url = reverse('dashboard:home')
            if request.user.is_superuser or emp.is_hr():
                pending_leave_count = LeaveRequest.objects.filter(
                    Q(status=LeaveRequest.STATUS_MANAGER_APPROVED, employee__requires_nurse_supt=False) |
                    Q(status=LeaveRequest.STATUS_MANAGER_APPROVED, employee__nurse_superintendent__isnull=True) |
                    Q(status=LeaveRequest.STATUS_NURSE_SUPT_APPROVED)
                ).distinct().count()
                pending_leave_url = reverse('leaves:hr_approvals')
                pending_discipline_proposals = DisciplineRecord.objects.filter(
                    is_proposal=True
                ).count()
            elif emp.role in ('admin_director', 'finance_director') or emp.acting_role in ('admin_director', 'finance_director'):
                pending_leave_count = LeaveRequest.objects.filter(
                    status=LeaveRequest.STATUS_HR_APPROVED
                ).exclude(
                    Q(employee__role__in=('admin_director', 'medical_director')) | Q(employee__reports_to_ceo=True)
                ).count()
                pending_leave_url = reverse('leaves:director_approvals')
                if emp.role == 'admin_director' or emp.acting_role == 'admin_director':
                    pending_discipline_proposals = DisciplineRecord.objects.filter(
                        is_proposal=True
                    ).count()
            elif emp.is_manager() or emp.is_director():
                pending_leave_count = LeaveRequest.objects.filter(
                    Q(status=LeaveRequest.STATUS_PENDING, employee__unit_head__isnull=True) |
                    Q(status=LeaveRequest.STATUS_UNIT_HEAD_APPROVED) |
                    Q(status=LeaveRequest.STATUS_NURSE_SUPT_APPROVED, employee__role='manager', employee__requires_nurse_supt=True)
                ).filter(employee__supervisor=emp).distinct().count()
                pending_leave_url = reverse('leaves:manager_approvals')
            elif emp.role == 'unit_head':
                pending_leave_count = LeaveRequest.objects.filter(
                    status=LeaveRequest.STATUS_PENDING,
                    employee__unit_head=emp,
                ).count()
                pending_leave_url = reverse('leaves:unit_head_approvals')
            elif emp.role == 'nurse_superintendent':
                pending_leave_count = LeaveRequest.objects.filter(
                    status=LeaveRequest.STATUS_MANAGER_APPROVED,
                    employee__requires_nurse_supt=True,
                    employee__nurse_superintendent=emp,
                ).count()
                pending_leave_url = reverse('leaves:nurse_supt_approvals')

            # Pending consultations
            from leaves.models import LeaveConsultation
            pending_consultations_count = LeaveConsultation.objects.filter(
                consulted_with=emp,
                status=LeaveConsultation.STATUS_PENDING,
            ).count()

            # Medical sick leave LM badge — matches lm_queue view exactly
            from medical_leave.models import MedicalSickLeave
            if emp.is_manager() or emp.is_director():
                pending_medical_lm_count = MedicalSickLeave.objects.filter(
                    status=MedicalSickLeave.STATUS_PENDING_LINE_MANAGER,
                    employee__supervisor=emp,
                ).count()
        except Exception:
            pass

        return {
            'notif_unread': unread,
            'notif_recent': recent,
            'is_suspended': is_suspended,
            'suspension_end': suspension_end,
            'pending_coworker_count': pending_coworker_count,
            'pending_leave_count': pending_leave_count,
            'pending_leave_url': pending_leave_url,
            'pending_medical_lm_count': pending_medical_lm_count,
            'pending_discipline_proposals': pending_discipline_proposals,
            'pending_consultations_count': pending_consultations_count,
            'appraisal_self_count': appraisal_self_count,
            'appraisal_unit_head_count': appraisal_unit_head_count,
            'appraisal_manager_count': appraisal_manager_count,
            'appraisal_hr_count': appraisal_hr_count,
            'appraisal_director_count': appraisal_director_count,
            'appraisal_ceo_count': appraisal_ceo_count,
            'pending_appraisals_count': (
                appraisal_self_count + pending_coworker_count +
                appraisal_unit_head_count + appraisal_manager_count +
                appraisal_hr_count + appraisal_director_count + appraisal_ceo_count
            ),
        }
    except Exception:
        return {
            'notif_unread': 0,
            'notif_recent': [],
            'is_suspended': False,
            'suspension_end': None,
            'pending_coworker_count': 0,
            'pending_leave_count': 0,
            'pending_leave_url': '',
            'pending_medical_lm_count': 0,
            'pending_discipline_proposals': 0,
            'pending_consultations_count': 0,
            'appraisal_self_count': 0,
            'appraisal_unit_head_count': 0,
            'appraisal_manager_count': 0,
            'appraisal_hr_count': 0,
            'appraisal_director_count': 0,
            'appraisal_ceo_count': 0,
            'pending_appraisals_count': 0,
        }
