"""Leave entitlement tiers based on years of service."""

from datetime import date as _date


def seniority_entitlement(emp, year=None):
    """
    Return the annual leave entitlement (days) for *emp* in *year*
    based on their date_joined_company:

        0 – 5  years  →  18 days
        6 – 10 years  →  20 days
        > 10   years  →  22 days

    Falls back to 18 if date_joined_company is unknown.
    """
    if not getattr(emp, 'date_joined_company', None):
        return 18

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
        return 18
    elif years <= 10:
        return 20
    else:
        return 22
