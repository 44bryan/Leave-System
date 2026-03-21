# MICEI HRM — Claude Continuation Guide
### Read this file before continuing development with Claude

---

## What This System Is

**MICEI HRM** is a Django-based HR leave management system built for **Magrabi ICO Cameroon Eye Institute** (Cameroon). It manages employee leave requests through a 3-stage approval workflow: Line Manager → HR Admin → Administration Director.

**Tech stack:** Django 5.0.6, Python 3.11, SQLite, Bootstrap 5.3, Bootstrap Icons, Django i18n (English/French).

**Root directory:** `c:\Users\bry30\Desktop\leave_system\`

---

## Project Structure

```
leave_system/
├── leave_system/         # Django project settings
│   ├── settings.py
│   └── urls.py
├── accounts/             # User & employee management app
│   ├── models.py         # Department, Employee
│   ├── views.py          # Login, profile, employee CRUD, password reset
│   ├── forms.py          # ChangePasswordForm, AdminResetCredentialsForm
│   ├── urls.py
│   └── templates/accounts/
│       ├── login.html
│       ├── profile.html
│       ├── employee_list.html
│       ├── employee_form.html
│       ├── change_password.html
│       └── admin_reset_credentials.html
├── leaves/               # Leave requests app
│   ├── models.py         # LeaveType, LeaveRequest, LeaveBalance
│   ├── views.py          # All leave views including admin overrides
│   ├── forms.py          # LeaveRequestForm, ApprovalForm
│   ├── urls.py
│   └── templates/leaves/
│       ├── request_form.html
│       ├── my_requests.html
│       ├── leave_detail.html
│       ├── action_form.html           # Shared approve/reject form
│       ├── manager_approvals.html
│       ├── hr_approvals.html
│       ├── director_approvals.html
│       ├── all_leaves.html
│       ├── leave_print.html
│       ├── employee_leave_summary.html
│       ├── leave_type_list.html       # Admin: manage leave types
│       └── leave_type_form.html       # Admin: add/edit leave type
├── dashboard/            # Dashboards & admin settings app
│   ├── views.py          # All dashboard views + admin settings
│   ├── urls.py
│   └── templates/dashboard/
│       ├── admin_dashboard.html
│       ├── employee_dashboard.html
│       ├── manager_dashboard.html
│       ├── hr_dashboard.html
│       ├── director_dashboard.html
│       ├── leave_tracker.html
│       └── admin_settings.html
├── templates/
│   └── base.html         # Global base template (sidebar, topbar, search, JS)
├── static/
│   └── LOGO.png
├── media/                # Uploaded supporting documents
├── USER_MANUAL.md        # End-user documentation
└── CLAUDE_CONTINUATION_GUIDE.md  # This file
```

---

## Key Models

### `accounts/models.py`

```python
class Department(models.Model):
    name = CharField
    code = CharField(unique=True)

class Employee(models.Model):
    user = OneToOneField(User, related_name='employee')
    employee_id = CharField(unique=True)
    department = ForeignKey(Department, null=True)
    role = CharField  # 'employee' | 'manager' | 'hr' | 'admin_director'
    supervisor = ForeignKey('self', null=True)  # points to their line manager
    position = CharField
    phone = CharField
    date_joined_company = DateField
    is_active = BooleanField

    # Key helper methods:
    is_hr()        # role == 'hr'
    is_manager()   # role == 'manager'
    is_director()  # role == 'admin_director'
```

### `leaves/models.py`

```python
class LeaveType(models.Model):
    name = CharField
    description = TextField
    requires_document = BooleanField
    color = CharField          # Bootstrap color name: 'primary', 'danger', etc.
    is_active = BooleanField
    is_deductible = BooleanField  # True = subtracts from annual balance

class LeaveRequest(models.Model):
    # Status constants:
    STATUS_PENDING           = 'pending'
    STATUS_MANAGER_APPROVED  = 'manager_approved'
    STATUS_HR_APPROVED       = 'hr_approved'
    STATUS_APPROVED          = 'approved'
    STATUS_REJECTED_MANAGER  = 'rejected_manager'
    STATUS_REJECTED_HR       = 'rejected_hr'
    STATUS_REJECTED_DIRECTOR = 'rejected_director'
    STATUS_CANCELLED         = 'cancelled'

    employee = ForeignKey(Employee)
    leave_type = ForeignKey(LeaveType)
    start_date, end_date = DateField
    total_days = PositiveIntegerField  # auto-calculated on save()
    reason = TextField
    supporting_document = FileField(null=True)
    status = CharField

    # Approval chain fields (manager / hr / director):
    manager_action_by, hr_action_by, director_action_by = ForeignKey(Employee, null=True)
    manager_action_date, hr_action_date, director_action_date = DateTimeField(null=True)
    manager_remarks, hr_remarks, director_remarks = TextField(blank=True)

    # IMPORTANT: save() auto-calculates total_days from _count_working_days()
    # Mon–Sat only (Sunday = weekday 6 is excluded)
    # To override total_days without recalculating, use:
    # LeaveRequest.objects.filter(pk=pk).update(total_days=N)

    can_cancel()  # True if status is pending/manager_approved/hr_approved

class LeaveBalance(models.Model):
    employee = ForeignKey(Employee, related_name='leave_balances')
    year = PositiveIntegerField
    total_entitlement = PositiveIntegerField(default=18)

    # Computed properties (not stored in DB):
    used_days           # sum of total_days where status='approved' AND is_deductible=True
    remaining_days      # total_entitlement - used_days
    usage_percentage    # (used_days / total_entitlement) * 100

    # Methods:
    non_deductible_by_type()  # list of {name, days} for non-deductible approved leaves this year
    non_deductible_total()    # total non-deductible days this year
```

---

## URL Namespaces

| App | Namespace | Example URL |
|---|---|---|
| accounts | `accounts:` | `accounts:login`, `accounts:profile`, `accounts:employee_list` |
| leaves | `leaves:` | `leaves:submit`, `leaves:my_requests`, `leaves:detail` |
| dashboard | `dashboard:` | `dashboard:home`, `dashboard:admin_settings`, `dashboard:tracker` |

### Important Named URLs

```
accounts:login                    /accounts/login/
accounts:logout                   /accounts/logout/
accounts:profile                  /accounts/profile/
accounts:change_password          /accounts/profile/change-password/
accounts:employee_list            /accounts/employees/
accounts:reset_credentials/<pk>   /accounts/employees/<pk>/reset-credentials/

leaves:submit                     /leaves/submit/
leaves:my_requests                /leaves/my-requests/
leaves:detail <pk>                /leaves/detail/<pk>/
leaves:cancel <pk>                /leaves/cancel/<pk>/
leaves:manager_approvals          /leaves/manager/pending/
leaves:manager_action <pk>        /leaves/manager/action/<pk>/
leaves:hr_approvals               /leaves/hr/pending/
leaves:hr_action <pk>             /leaves/hr/action/<pk>/
leaves:all_leaves                 /leaves/hr/all/
leaves:director_approvals         /leaves/director/pending/
leaves:director_action <pk>       /leaves/director/action/<pk>/
leaves:print_leave <pk>           /leaves/print/<pk>/
leaves:employee_summary <pk>      /leaves/employee/<pk>/summary/
leaves:admin_override <pk>        /leaves/admin-override/<pk>/
leaves:admin_edit <pk>            /leaves/admin-edit/<pk>/
leaves:leave_type_list            /leaves/leave-types/
leaves:leave_type_create          /leaves/leave-types/add/
leaves:leave_type_edit <pk>       /leaves/leave-types/<pk>/edit/
leaves:leave_type_delete <pk>     /leaves/leave-types/<pk>/delete/
leaves:restore_default_leave_types /leaves/leave-types/restore-defaults/

dashboard:home                    /dashboard/
dashboard:tracker                 /dashboard/tracker/
dashboard:search                  /dashboard/search/     (JSON API)
dashboard:admin_settings          /dashboard/admin-settings/
dashboard:reset_balances          /dashboard/admin-settings/reset-balances/
dashboard:reset_single_balance<pk>/dashboard/admin-settings/reset-balance/<pk>/
dashboard:adjust_entitlement<pk>  /dashboard/admin-settings/adjust-entitlement/<pk>/
dashboard:export_data             /dashboard/admin-settings/export/
dashboard:import_data             /dashboard/admin-settings/import/
dashboard:factory_reset_full      /dashboard/admin-settings/factory-reset/full/
dashboard:factory_reset_soft      /dashboard/admin-settings/factory-reset/soft/
```

---

## Approval Workflow

```
Employee submits → status: 'pending'
    ↓ Manager approves
status: 'manager_approved'
    ↓ HR approves
status: 'hr_approved'
    ↓ Director approves
status: 'approved'  ← Final. Employee can print approval letter.

At any stage, rejection sets status to:
  rejected_manager | rejected_hr | rejected_director

Employee or admin can cancel: status → 'cancelled'
Admin can revert to pending: clears all action fields, status → 'pending'
```

---

## Leave Balance Logic

- `used_days` is a **computed property** — it sums `total_days` from all `approved` requests where `leave_type__is_deductible=True` for the given year.
- **No stored balance counter.** Cancelling or editing an approved leave immediately changes the balance because the property is recomputed on every access.
- To correct days after an approved leave: use `LeaveRequest.objects.filter(pk=pk).update(total_days=N)` — this bypasses `save()` so the dates don't recalculate the days.

---

## Default Leave Types

| Name | Deductible | Document |
|---|---|---|
| Annual Leave | YES | No |
| Permission | YES | No |
| Permission for School Leave | YES | Yes |
| Sick Leave | No | Yes |
| Maternity Leave | No | Yes |
| Paternity Leave | No | Yes |
| Marriage Leave | No | No |
| Compassionate Leave | No | No |
| Study Leave | No | No |

To restore them programmatically:
```python
from leaves.views import seed_default_leave_types
seed_default_leave_types()  # uses get_or_create — safe to run multiple times
```

---

## Working Days Calculation

```python
# In LeaveRequest.save() — counts Mon–Sat, excludes Sunday (weekday() == 6)
@staticmethod
def _count_working_days(start, end):
    from datetime import timedelta
    count = 0
    current = start
    while current <= end:
        if current.weekday() != 6:  # 6 = Sunday
            count += 1
        current += timedelta(days=1)
    return count
```

---

## Role-Based Access Patterns

```python
# In views.py — standard access check pattern:
employee = get_employee(request)     # returns Employee or None
if not employee or not employee.is_manager():
    messages.error(request, "Access denied.")
    return redirect('dashboard:home')

# Superuser-only decorator used in dashboard/views.py:
@superuser_required_view
def some_admin_view(request): ...

# In base.html sidebar — role checks:
{% if user.employee.is_manager %}   # shows Manager Queue
{% if user.employee.is_hr %}        # shows HR section
{% if user.employee.is_director %}  # shows Director section
{% if user.is_superuser %}          # shows Admin section
```

---

## Important Implementation Notes

1. **`leave.save()` always recalculates `total_days`** from start/end dates. If you need to set `total_days` manually (e.g. admin correction), use `queryset.update()` instead of `instance.save()`.

2. **Action views are crash-proof** — `manager_action`, `hr_action`, `director_action` all fetch the leave by pk only (no status filter in `get_object_or_404`), then validate the status separately with a user-friendly message redirect instead of a 404.

3. **Supervisor filter** — Manager can only action leaves where `leave.employee.supervisor == manager_employee`. Superusers bypass this check.

4. **Password force-change** — After factory reset, admin password is set to `'admin'`. The `home` view checks `request.user.check_password('admin')` and redirects superusers to `change_password` if it matches.

5. **Soft reset** keeps: users, employees, departments, leave types. Deletes: leave requests and balances only.

6. **Full factory reset** deletes everything, resets admin to `admin`/`admin`, then calls `seed_default_leave_types()` to recreate the 9 default leave types.

7. **Search API** at `dashboard:search` returns JSON with `results` array. Each result has `type`, `title`, `subtitle`, `url`, and optionally `initials` or `icon`. Role-based: non-HR/admin users only see employees and their own leaves.

8. **Live search** in `base.html` uses fetch with 280ms debounce, grouped results dropdown.

9. **i18n** — All templates use `{% load i18n %}` and `{% trans "..." %}`. Language switcher in top bar switches between English and French.

---

## Migrations

```
accounts: 0001_initial, 0002_...
leaves:   0001_initial, 0002_..., 0003_add_is_deductible_to_leavetype, 0004_seed_default_leave_types
```

To run all migrations: `python manage.py migrate`

---

## Running the Server

```bash
cd c:/Users/bry30/Desktop/leave_system
# Activate venv first:
source venv/Scripts/activate        # Windows Git Bash
# OR:
venv\Scripts\activate               # Windows CMD

python manage.py runserver
# Visit: http://127.0.0.1:8000/
```

---

## Known Patterns / Conventions

- All templates extend `templates/base.html`.
- Page title block: `{% block page_title %}`, subtitle: `{% block page_subtitle %}`.
- Active sidebar link: each template sets e.g. `{% block nav_dashboard %}active{% endblock %}`.
- Topbar action buttons: `{% block topbar_actions %}`.
- Bootstrap 5.3 classes throughout. Custom CSS variables in `base.html` `<style>` block.
- Card style: `border-radius:16px`, `border: 1px solid #cde8ef`.
- Primary brand colour: `#0891a8` (teal). Sidebar: white with teal accents.
- Messages framework used everywhere for success/error/warning feedback.

---

*Last updated: March 2026 — MICEI HRM v1.0*
