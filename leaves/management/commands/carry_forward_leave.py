from django.core.management.base import BaseCommand
from datetime import date
from leaves.models import LeaveBalance
from leaves.seniority import seniority_entitlement


class Command(BaseCommand):
    help = 'Carry forward unused deductible leave to the next year as accumulated leave.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from-year',
            type=int,
            default=date.today().year - 1,
            help='Source year to carry forward from (default: last year)',
        )

    def handle(self, *args, **options):
        from_year = options['from_year']
        to_year = from_year + 1

        balances = LeaveBalance.objects.filter(year=from_year).select_related('employee')
        if not balances.exists():
            self.stdout.write(self.style.WARNING(
                f'No leave balances found for {from_year}. Nothing to carry forward.'
            ))
            return

        count = 0
        total_days = 0
        for bal in balances:
            carry = bal.remaining_days
            next_bal, created = LeaveBalance.objects.get_or_create(
                employee=bal.employee,
                year=to_year,
                defaults={
                    'total_entitlement': seniority_entitlement(bal.employee, to_year),
                    'carried_forward': carry,
                },
            )
            if not created:
                next_bal.carried_forward = carry
                next_bal.save()
            total_days += carry
            count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Carry-forward complete: {count} employees, '
            f'{total_days} days carried from {from_year} → {to_year}.'
        ))
