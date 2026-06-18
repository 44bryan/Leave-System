"""
Management command: auto_lock_expired_contracts

Locks the login account of any employee whose most recent fixed-term
contract (CDD / INTERN / WACS) expired more than `grace_days` ago with
no active renewal. Only runs if contract_auto_lock_enabled is True in
SystemSettings (or --force is passed).

Usage:
    python manage.py auto_lock_expired_contracts
    python manage.py auto_lock_expired_contracts --force --grace-days 30
    python manage.py auto_lock_expired_contracts --dry-run
"""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Lock accounts of employees with expired fixed-term contracts past the grace period.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would be locked without actually locking.')
        parser.add_argument('--force', action='store_true',
                            help='Run even if auto-lock is disabled in SystemSettings.')
        parser.add_argument('--grace-days', type=int, default=None,
                            help='Override the grace period in days (default: from SystemSettings).')

    def handle(self, *args, **options):
        from dashboard.models import SystemSettings
        from contracts.models import Contract
        from accounts.models import Employee

        ss = SystemSettings.get()
        dry_run = options['dry_run']
        force   = options['force']

        if not ss.contract_auto_lock_enabled and not force:
            self.stdout.write(self.style.WARNING(
                'Auto-lock is disabled in System Settings. Use --force to run anyway.'
            ))
            return

        grace_days = options['grace_days'] if options['grace_days'] is not None else ss.contract_auto_lock_grace_days
        cutoff = date.today() - timedelta(days=grace_days)

        self.stdout.write(f'Grace period: {grace_days} days (cutoff: {cutoff})')

        # Find employees whose LATEST fixed-term contract ended before the cutoff
        # and have NO active contract at all.
        locked_count   = 0
        unlocked_count = 0

        employees = Employee.objects.select_related('user').filter(is_active=True)

        for emp in employees:
            contracts = emp.contracts.filter(contract_type__in=('CDD', 'INTERN', 'WACS'))
            if not contracts.exists():
                continue

            has_active = contracts.filter(status='active').exists()
            if has_active:
                # Employee has a current active contract — ensure account is unlocked
                if not emp.user.is_active:
                    if not dry_run:
                        emp.user.is_active = True
                        emp.user.save(update_fields=['is_active'])
                    unlocked_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'  UNLOCKED: {emp.get_full_name()} ({emp.employee_id}) — active contract found'
                    ))
                continue

            # No active contract — check the most recent end date
            latest = contracts.order_by('-end_date').first()
            if not latest or not latest.end_date:
                continue

            if latest.end_date < cutoff:
                if emp.user.is_active:
                    if not dry_run:
                        emp.user.is_active = False
                        emp.user.save(update_fields=['is_active'])
                    locked_count += 1
                    self.stdout.write(self.style.WARNING(
                        f'  LOCKED: {emp.get_full_name()} ({emp.employee_id}) — '
                        f'contract ended {latest.end_date} ({(date.today() - latest.end_date).days} days ago)'
                    ))

        prefix = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\n{prefix}Done. Locked: {locked_count}, Unlocked: {unlocked_count}'
        ))
