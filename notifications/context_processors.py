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
        pending_discipline_proposals = 0
        pending_appraisals_count = 0
        pending_consultations_count = 0

        try:
            emp = request.user.employee
            from discipline.models import DisciplineRecord
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

            # Appraisal pending counts (all roles)
            from appraisals.models import AppraisalRecord
            from django.db.models import Q
            pending_coworker_count = AppraisalRecord.objects.filter(
                coworker_signed_by=emp,
                status=AppraisalRecord.STATUS_COWORKER,
            ).count()
            _aq = (
                Q(status=AppraisalRecord.STATUS_EMPLOYEE, employee=emp) |
                Q(status=AppraisalRecord.STATUS_COWORKER, coworker_signed_by=emp) |
                Q(status=AppraisalRecord.STATUS_UNIT_HEAD, employee__supervisor=emp) |
                Q(status=AppraisalRecord.STATUS_MANAGER, employee__supervisor=emp)
            )
            if emp.is_hr():
                _aq |= Q(status=AppraisalRecord.STATUS_HR)
            if emp.is_director():
                _aq |= Q(status=AppraisalRecord.STATUS_DIRECTOR)
            if emp.is_ceo():
                _aq |= Q(status=AppraisalRecord.STATUS_CEO)
            pending_appraisals_count = AppraisalRecord.objects.filter(_aq).count()

            # Sidebar badge counts — role-specific pending approval queues
            from leaves.models import LeaveRequest
            from django.urls import reverse
            pending_leave_url = reverse('dashboard:home')
            if request.user.is_superuser or emp.is_hr():
                from django.db.models import Q
                pending_leave_count = LeaveRequest.objects.filter(
                    Q(status=LeaveRequest.STATUS_MANAGER_APPROVED, employee__requires_nurse_supt=False) |
                    Q(status=LeaveRequest.STATUS_MANAGER_APPROVED, employee__nurse_superintendent__isnull=True) |
                    Q(status=LeaveRequest.STATUS_NURSE_SUPT_APPROVED)
                ).distinct().count()
                pending_leave_url = reverse('leaves:hr_approvals')
                pending_discipline_proposals = DisciplineRecord.objects.filter(
                    is_proposal=True
                ).count()
            elif emp.role == 'admin_director':
                pending_leave_count = LeaveRequest.objects.filter(
                    status=LeaveRequest.STATUS_HR_APPROVED
                ).count()
                pending_leave_url = reverse('leaves:director_approvals')
                pending_discipline_proposals = DisciplineRecord.objects.filter(
                    is_proposal=True
                ).count()
            elif emp.role == 'finance_director':
                pending_leave_count = LeaveRequest.objects.filter(
                    status=LeaveRequest.STATUS_HR_APPROVED
                ).count()
                pending_leave_url = reverse('leaves:director_approvals')
            elif emp.is_manager():
                pending_leave_count = LeaveRequest.objects.filter(
                    status=LeaveRequest.STATUS_UNIT_HEAD_APPROVED,
                    employee__supervisor=emp,
                ).count()
                # Also count "pending" for employees without a unit head
                pending_leave_count += LeaveRequest.objects.filter(
                    status=LeaveRequest.STATUS_PENDING,
                    employee__supervisor=emp,
                    employee__unit_head__isnull=True,
                ).count()
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

            # Pending consultations sent to this user
            from leaves.models import LeaveConsultation
            pending_consultations_count = LeaveConsultation.objects.filter(
                consulted_with=emp,
                status=LeaveConsultation.STATUS_PENDING,
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
            'pending_discipline_proposals': pending_discipline_proposals,
            'pending_appraisals_count': pending_appraisals_count,
            'pending_consultations_count': pending_consultations_count,
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
            'pending_discipline_proposals': 0,
            'pending_appraisals_count': 0,
            'pending_consultations_count': 0,
        }
