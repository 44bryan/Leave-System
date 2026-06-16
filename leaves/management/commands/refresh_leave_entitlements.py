"""
Management command: refresh_leave_entitlements

Updates the total_entitlement on existing LeaveBalance records to match
the seniority tier based on date_joined_company.

Usage:
    python manage.py refresh_leave_entitlements           # current year
    python manage.py refresh_leave_entitlements --year 2025
    python manage.py refresh_leave_entitlements --dry-run
"""
from datetime import date

from django.core.management.base import BaseCommand

from leaves.models import LeaveBalance
from leaves.seniority import seniority_entitlement


class Command(BaseCommand):
    help = 'Recalculate leave entitlements for all employees based on seniority tiers.'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, default=date.today().year,
                            help='Year to update (default: current year)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would change without saving')

    def handle(self, *args, **options):
        year = options['year']
        dry = options['dry_run']

        balances = LeaveBalance.objects.filter(year=year).select_related(
            'employee', 'employee__user'
        )
        if not balances.exists():
            self.stdout.write(self.style.WARNING(f'No leave balances found for {year}.'))
            return

        updated = 0
        skipped = 0
        for bal in balances:
            correct = seniority_entitlement(bal.employee, year)
            if bal.total_entitlement != correct:
                self.stdout.write(
                    f"  {'[DRY]' if dry else 'UPDATE'} "
                    f"{bal.employee.get_full_name()}: "
                    f"{bal.total_entitlement} → {correct} days"
                )
                if not dry:
                    bal.total_entitlement = correct
                    bal.save(update_fields=['total_entitlement'])
                updated += 1
            else:
                skipped += 1

        action = 'Would update' if dry else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} {updated} balance(s). {skipped} already correct.'
        ))
