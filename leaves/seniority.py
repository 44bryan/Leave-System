"""Leave entitlement tiers based on years of service + children bonus."""

from datetime import date as _date

# Maximum extra days an employee can earn from having children
MAX_CHILD_BONUS_DAYS = 4


def _child_bonus_days(emp):
    """
    Return extra leave days for children: +2 days per child, max MAX_CHILD_BONUS_DAYS.
    Counts all children (beneficiary and non-beneficiary) registered in HealthDependant.
    """
    child_count = emp.health_dependants.filter(
        relation__in=('child_ben', 'child_other')
    ).count()
    return min(child_count * 2, MAX_CHILD_BONUS_DAYS)


def seniority_entitlement(emp, year=None):
    """
    Return the annual leave entitlement (days) for *emp* in *year*
    based on their date_joined_company + children bonus:

        0 – 5  years  →  18 days
        6 – 10 years  →  20 days
        > 10   years  →  22 days
        + 1 day per child (max 4)

    Falls back to 18 if date_joined_company is unknown.
    """
    if not getattr(emp, 'date_joined_company', None):
        base = 18
    else:
        ref_year = year or _date.today().year
        years = ref_year - emp.date_joined_company.year

        # If their anniversary hasn't occurred yet this year, subtract 1
        try:
            anniversary = emp.date_joined_company.replace(year=ref_year)
            if anniversary > _date.today():
                years -= 1
        except ValueError:
            pass  # Feb 29 edge case — ignore

        years = max(years, 0)

        if years < 6:
            base = 18
        elif years <= 10:
            base = 20
        else:
            base = 22

    return base + _child_bonus_days(emp)
