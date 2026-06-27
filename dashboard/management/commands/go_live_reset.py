"""
Management command: go_live_reset
Wipes all test/transactional data before going live.

Keeps:  employees, user accounts, departments, contracts,
        employee documents, leave types, system settings.

Clears: appraisals, leave requests, leave balances, discipline records,
        notifications, payslips, audit logs, login attempt logs.

Usage:
    python manage.py go_live_reset           # shows counts + asks for confirmation
    python manage.py go_live_reset --yes     # skips confirmation prompt
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Wipe test data before go-live. Keeps employees, contracts, documents.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt and proceed immediately.',
        )

    def handle(self, *args, **options):
        from appraisals.models import AppraisalCycle, AppraisalRecord
        from leaves.models import LeaveRequest, LeaveBalance, LeaveConsultation, LeaveReversal
        from discipline.models import DisciplineRecord
        from notifications.models import Notification
        from payroll.models import Payslip
        from dashboard.models import AuditLog
        from contracts.models import ContractNotification
        from accounts.models import OnboardingChecklist
        from recognition.models import RecognitionProposal, RecognitionComment
        from recruitment.models import Application, ApplicationAnswer, JobPosting

        # Try to clear axes (brute-force login attempt logs) — optional dependency
        try:
            from axes.models import AccessAttempt, AccessLog
            axes_attempts = AccessAttempt.objects.count()
            axes_logs = AccessLog.objects.count()
        except Exception:
            axes_attempts = axes_logs = None

        counts = {
            'Appraisal Cycles':        AppraisalCycle.objects.count(),
            'Appraisal Records':       AppraisalRecord.objects.count(),
            'Leave Requests':          LeaveRequest.objects.count(),
            'Leave Consultations':     LeaveConsultation.objects.count(),
            'Leave Reversals':         LeaveReversal.objects.count(),
            'Leave Balances':          LeaveBalance.objects.count(),
            'Discipline Records':      DisciplineRecord.objects.count(),
            'Notifications':           Notification.objects.count(),
            'Payslips':                Payslip.objects.count(),
            'Audit Logs':              AuditLog.objects.count(),
            'Contract Notifications':  ContractNotification.objects.count(),
            'Recognition Proposals':   RecognitionProposal.objects.count(),
            'Recognition Comments':    RecognitionComment.objects.count(),
            'Job Applications':        Application.objects.count(),
            'Application Answers':     ApplicationAnswer.objects.count(),
            'Job Postings':            JobPosting.objects.count(),
            'Onboarding flags reset':  OnboardingChecklist.objects.count(),
        }
        if axes_attempts is not None:
            counts['Login Attempt Logs'] = axes_attempts + axes_logs

        self.stdout.write('\n' + '=' * 55)
        self.stdout.write('  GO-LIVE RESET — records to be cleared:')
        self.stdout.write('=' * 55)
        for label, count in counts.items():
            self.stdout.write(f'  {label:<30} {count:>6}')
        self.stdout.write('=' * 55)
        self.stdout.write(self.style.WARNING(
            '\n  KEPT: employees, users, departments, contracts,\n'
            '        employee documents, leave types, system settings,\n'
            '        job posting configs (form fields & scoring criteria).\n'
        ))

        if not options['yes']:
            confirm = input('  Type YES to proceed: ').strip()
            if confirm != 'YES':
                self.stdout.write(self.style.ERROR('Aborted.'))
                return

        self.stdout.write('\nClearing data...')

        AppraisalRecord.objects.all().delete()
        AppraisalCycle.objects.all().delete()
        self.stdout.write('  [OK] Appraisals cleared')

        LeaveConsultation.objects.all().delete()
        LeaveReversal.objects.all().delete()
        LeaveRequest.objects.all().delete()
        LeaveBalance.objects.all().delete()
        self.stdout.write('  [OK] Leave requests, consultations, reversals and balances cleared')

        DisciplineRecord.objects.all().delete()
        self.stdout.write('  [OK] Discipline records cleared')

        Notification.objects.all().delete()
        self.stdout.write('  [OK] Notifications cleared')

        Payslip.objects.all().delete()
        self.stdout.write('  [OK] Payslips cleared')

        AuditLog.objects.all().delete()
        self.stdout.write('  [OK] Audit logs cleared')

        ContractNotification.objects.all().delete()
        self.stdout.write('  [OK] Contract notifications cleared')

        RecognitionComment.objects.all().delete()
        RecognitionProposal.objects.all().delete()
        self.stdout.write('  [OK] Recognition data cleared')

        ApplicationAnswer.objects.all().delete()
        Application.objects.all().delete()
        JobPosting.objects.all().delete()
        self.stdout.write('  [OK] Recruitment applications and job postings cleared')

        # Reset onboarding checklist flags but keep the records
        OnboardingChecklist.objects.all().update(
            issue_contract=False,
            set_leave_balance=False,
            assign_manager=False,
            profile_photo=False,
            signature_captured=False,
            credentials_sent=False,
            id_document_uploaded=False,
            notes='',
        )
        self.stdout.write('  [OK] Onboarding checklists reset to unchecked')

        if axes_attempts is not None:
            try:
                from axes.models import AccessAttempt, AccessLog
                AccessAttempt.objects.all().delete()
                AccessLog.objects.all().delete()
                self.stdout.write('  [OK] Login attempt logs cleared')
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS(
            '\n  System reset complete. Ready for go-live.\n'
        ))
