import json


def system_settings_ctx(request):
    try:
        from .models import SystemSettings
        return {'system_settings': SystemSettings.get()}
    except Exception:
        return {'system_settings': None}


def all_employees_ctx(request):
    """Inject all active employees as JSON for client-side search (no AJAX needed)."""
    if not request.user.is_authenticated:
        return {'all_employees_json': '[]'}
    try:
        from accounts.models import Employee
        qs = Employee.objects.filter(is_active=True).select_related('user', 'department')
        data = [
            {
                'id': e.pk,
                'name': e.get_full_name(),
                'emp_id': e.employee_id or '',
                'dept': str(e.department) if e.department else '',
                'role': e.get_role_display(),
                'label': e.get_full_name() + (' (' + e.employee_id + ')' if e.employee_id else ''),
            }
            for e in qs
        ]
        return {'all_employees_json': json.dumps(data)}
    except Exception:
        return {'all_employees_json': '[]'}
