# LeaveDesk HR System — Project Document

## What Is This Application?

LeaveDesk is a web-based Leave Management System built for an Eye Hospital. It allows staff to submit leave requests digitally, which go through a two-stage approval process (Line Manager → HR Admin) before being fully approved. The system tracks leave balances automatically and gives each role a customized view of what concerns them.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, Django 5.0.6 |
| Database | SQLite (file: `db.sqlite3`) |
| Frontend | Bootstrap 5, Bootstrap Icons, Chart.js |
| Font | Plus Jakarta Sans (Google Fonts) |

---

## How to Run the Application

### Prerequisites
- Python 3.11 or 3.12 installed
- The project folder is at: `C:\Users\bry30\Desktop\leave_system`

### Start the Server

Open a terminal and run:

```bash
cd C:\Users\bry30\Desktop\leave_system
venv\Scripts\python.exe manage.py runserver
```

Then open your browser at: **http://127.0.0.1:8000**

---

## Login Credentials

| Role | Username | Password | Access Level |
|------|----------|----------|-------------|
| **Administrator** | `admin` | `Admin@2024` | Full access — sees everything |
| **HR Admin** | `hr_admin` | `hospital2024` | Leave approvals, tracker, all requests |
| **Line Manager** | `dr_fon` | `hospital2024` | Approves team leave requests |
| **Employee** | `nurse_mary` | `hospital2024` | Submit and view own leave requests |

---

## User Roles & What Each Can See

### Administrator (`admin`)
The admin is the root/superuser account. It has a full web profile like other users.

**Can do everything:**
- View the full HR Dashboard (stats, charts, monthly trends)
- See ALL pending leave requests from ALL employees (manager queue)
- Approve/reject leave at manager level and HR level
- View the leave tracker (all employee balances)
- **Add new employees** (web form at `/accounts/employees/add/`)
- **Edit employees** (change name, role, department, supervisor, etc.)
- **Delete employees** (with confirmation screen)
- Manage departments (add/delete)
- See all leave history

**Password can be changed** by logging in as admin, going to `/admin/` (Django Admin panel), then Users → admin → change password. Or ask another admin.

### HR Admin (`hr_admin`)
Handles the final stage of leave approval and monitors leave across the hospital.

**Can see:**
- HR Dashboard with stats and charts
- HR Approvals — manager-approved requests waiting for HR sign-off
- All Requests — complete leave history with filters (year, status, department)
- Leave Tracker — all employee leave balances

**Cannot:** add/delete employees, manage departments.

### Line Manager (`dr_fon`)
Handles the first stage of leave approval for their direct subordinates.

**Can see:**
- Manager Dashboard — pending approvals, team members, who is on leave today
- Manager Queue — pending leave requests from their direct reports
- Approve or reject with optional remarks

**Cannot:** see HR-level approvals or other teams' requests.

### Employee (`nurse_mary`)
Regular hospital staff member.

**Can:**
- Submit a leave request (choose type, dates, reason, attach document)
- View their own leave history and current status
- Cancel a pending request
- View their leave balance

**Cannot:** see other employees' requests.

---

## Leave Approval Workflow

```
Employee submits → Status: Pending
       ↓
Line Manager reviews → Approve → Status: Pending HR Approval
                     → Reject  → Status: Rejected by Manager
       ↓ (if approved)
HR Admin reviews   → Approve → Status: Approved ✓ (balance deducted)
                   → Reject  → Status: Rejected by HR
```

Leave balance is deducted **automatically** only when fully approved by HR.

---

## Leave Types (seeded)

1. Annual Leave
2. Sick Leave
3. Marriage Leave
4. Maternity Leave
5. Paternity Leave
6. Compassionate Leave
7. Study Leave

Each employee gets **18 days** per year by default.

---

## Departments (seeded)

- Ophthalmology
- Human Resources
- Administration
- Nursing
- Pharmacy
- IT & Support

---

## Project File Structure

```
leave_system/
├── manage.py                  ← Django entry point
├── requirements.txt           ← Python packages
├── db.sqlite3                 ← SQLite database (auto-created)
│
├── leave_system/              ← Django project config
│   ├── settings.py
│   └── urls.py
│
├── accounts/                  ← Users, employees, departments
│   ├── models.py              ← Employee, Department models
│   ├── views.py               ← Login, profile, employee CRUD
│   ├── forms.py               ← Login, create/edit employee forms
│   ├── admin.py               ← Django admin registration
│   └── templates/accounts/
│       ├── login.html
│       ├── profile.html
│       ├── employee_list.html
│       ├── employee_form.html
│       ├── employee_confirm_delete.html
│       └── department_list.html
│
├── leaves/                    ← Leave requests and approvals
│   ├── models.py              ← LeaveRequest, LeaveType, LeaveBalance
│   ├── views.py               ← Submit, approve, cancel, list views
│   ├── forms.py               ← LeaveRequest form, Approval form
│   ├── admin.py               ← Django admin registration
│   └── templates/leaves/
│       ├── request_form.html
│       ├── my_requests.html
│       ├── manager_approvals.html
│       ├── hr_approvals.html
│       ├── action_form.html
│       ├── leave_detail.html
│       └── all_leaves.html
│
├── dashboard/                 ← Role-specific dashboards
│   ├── views.py               ← HR/Manager/Employee dashboard logic
│   └── templates/dashboard/
│       ├── hr_dashboard.html
│       ├── manager_dashboard.html
│       ├── employee_dashboard.html
│       ├── leave_tracker.html
│       └── no_profile.html
│
└── templates/
    └── base.html              ← Shared layout, sidebar, topbar
```

---

## Key URLs

| URL | Description |
|-----|-------------|
| `/` | Redirects to dashboard |
| `/accounts/login/` | Login page |
| `/accounts/logout/` | Logout |
| `/accounts/profile/` | My profile |
| `/dashboard/` | Home dashboard (role-based) |
| `/dashboard/tracker/` | Leave tracker (HR/Admin only) |
| `/leaves/submit/` | Apply for leave |
| `/leaves/my-requests/` | My leave history |
| `/leaves/manager/pending/` | Manager approval queue |
| `/leaves/hr/pending/` | HR approval queue |
| `/leaves/hr/all/` | All leave requests |
| `/accounts/employees/` | Employee list (Admin only) |
| `/accounts/employees/add/` | Add employee (Admin only) |
| `/accounts/departments/` | Department management (Admin only) |
| `/admin/` | Django admin panel (superuser) |

---

## Common Tasks

### Add a new employee
1. Log in as `admin`
2. Go to sidebar → **Admin → Employees**
3. Click **Add Employee**
4. Fill in: First/Last name, email, username, password, Employee ID, department, role, supervisor
5. Save → employee can immediately log in

### Change an employee's password
1. Log in as `admin`
2. Go to `/admin/` → Users → find the user → change password
3. Or: ask the employee to contact admin

### Approve a leave request (as HR)
1. Log in as `hr_admin`
2. Sidebar → HR Approvals
3. Click **Final Review** on any request
4. Select Approve or Reject, add optional remarks, submit

### View all leave requests
1. Log in as `hr_admin` or `admin`
2. Sidebar → All Requests
3. Filter by year, status, department

---

## Notes for Future Development

- The database is SQLite (file-based) — suitable for local/small-scale use. For production, switch to PostgreSQL in `settings.py`.
- `DEBUG = True` and `SECRET_KEY` in `settings.py` must be changed before any production deployment.
- File uploads (supporting documents) are stored in `media/leave_docs/`.
- To reset the database: delete `db.sqlite3`, then run `python manage.py migrate` and `python manage.py seed_data`.

---

## How to Start the Server Locally (Correct Way)

```bash
cd C:\Users\bry30\Desktop\leave_system
source venv/Scripts/activate
python manage.py collectstatic --noinput   # only needed once or after static file changes
DEBUG=True python manage.py runserver
```

Then open: **http://127.0.0.1:8000**

> `DEBUG` defaults to `False` in settings.py. Always pass `DEBUG=True` when running locally so you get full error pages instead of generic 500 errors.

---

## Change Log

### 2026-03-12
- Fixed Server Error (500) on startup caused by missing staticfiles manifest
- Root cause: `STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'` requires running `collectstatic` before the server can serve any page
- Fix applied: ran `python manage.py collectstatic --noinput` — 128 files copied, 380 post-processed
- Server now runs correctly at http://127.0.0.1:8000
- No code changes were made; only static files were collected

- **Added Discipline Module** — new Django app `discipline/`
  - New model: `DisciplineRecord` with fields: employee, action_type, issued_by, date_issued, reason, document, suspension_start, suspension_end (auto = start+8 days), notes
  - Action types: Verbal Warning, Written Caution, Final Written Warning, Suspension (8 days fixed), Dismissal
  - HR Admin and Admin Director can issue all types; Line Manager can only issue Verbal Warning and Written Caution
  - Employees see only their own records; Managers see their team's records; HR/Admin see all
  - Dismissal keeps account active but shows a persistent banner alerting HR and Admin to deactivate manually
  - **New URLs:** `/discipline/` (list), `/discipline/issue/` (form), `/discipline/<id>/` (detail), `/discipline/stats/` (stats page)
  - Sidebar section "Discipline" visible to HR, Director, Manager, and Superuser
  - HR and Director dashboards now show discipline stats row: Warned / Suspended / Dismissed (clickable)
  - Employee dashboard shows red alert banner if they have any discipline notice; dark banner if actively suspended
  - Migration applied: `discipline/migrations/0001_initial.py`
---

- **Discipline module UX improvements (2026-03-12 session 2)**
  - Removed duplicate stat cards from Discipline Records list page — stats now live exclusively on Discipline Stats page and general dashboards
  - Cleaned up discipline_list view — no longer computes stats, only dismissal_alert for HR/Admin
  - Employee dashboard: replaced generic 'you have a discipline notice' banner with a tabbed card
    - Tab 1: Leave Requests (existing)
    - Tab 2: Discipline Notices — shows ALL notices with type badge, date, issued by, reason snippet, and View link
    - Tab badge shows red count if employee has any notices
    - Suspension banner at top is kept (critical visibility)
  - discipline_notices queryset now returns all records (no [:5] limit)

- **Dashboard reorganisation (2026-03-12 session 3)**
  - All four role dashboards (Manager, HR, Admin Director, Super Admin) fully reorganised with:
    - Clear section labels between groups (Overview / Discipline Overview / Action Required / Leave Activity / Analytics / Staff & System)
    - Action buttons moved to `{% block topbar_actions %}` so they appear in the teal topbar
    - Consistent stat card styling across all dashboards
  - Manager dashboard: fixed stat card style, added full-width pending approvals table, added Team Members card
  - HR dashboard: Action Required (pending approvals) moved above chart; section labels added; topbar actions: Leave Tracker + Issue Notice + HR Approvals
  - Director dashboard: Awaiting Final Approval table moved above chart; topbar actions: Issue Notice + Final Approvals
  - Admin dashboard: added Discipline Overview section (3 cards); added Discipline Records quick action link; topbar actions: Add Employee + System Settings
  - admin_dashboard view updated to fetch discipline_warned, discipline_suspended, discipline_dismissed

### 2026-03-15

- **Notification System** — full in-app + email notification system (`notifications/` app)
  - `Notification` model: recipient (FK User), title, message, type, url, is_read, created_at
  - Bell icon in topbar navbar with unread badge counter (shows up to 6 recent in dropdown)
  - Clicking a notification marks it read and redirects to the relevant page (url field)
  - Full notification list at `/notifications/` with Mark All Read
  - Context processor (`notifications_ctx`) injects `notif_unread` and `notif_recent` into every template
  - `notify()` utility function in `notifications/utils.py` — creates Notification + optionally sends email
  - Email: set `EMAIL_NOTIFICATIONS_ENABLED=True` in environment + SMTP vars (EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, etc.)
  - Triggers: leave submitted/approved/rejected, discipline issued, contract issued/renewed/terminated, account activated

- **Registration flow with mandatory contract** — employee create form now includes contract fields
  - `EmployeeCreateForm` has 3 new fields: `contract_type` (CDI/CDD), `contract_start_date`, `contract_end_date`
  - End date field shows/hides via JS based on selected contract type; required only for CDD
  - `employee_create` view creates Employee + Contract + LeaveBalance in a single transaction
  - Welcome `account_activated` notification sent to new employee automatically
  - Form template shows a teal "Initial Contract" section only for new employee creation

- **Discipline notifications** — when a discipline notice is issued, the employee now receives a bell notification
  - `discipline/views.py` calls `notify()` after `record.save()` with type `discipline`
  - Notification links directly to the discipline detail page

- **Contract bell notifications** — all contract events now also fire main bell notifications
  - Issue contract → `contract_issued` notification to employee
  - Renew contract → `contract_renewed` notification
  - Terminate contract → `contract_terminated` notification
  - These complement the existing `ContractNotification` records

- **HR Retirement Dashboard** — `/dashboard/retirement/`
  - Shows all active employees within 3 years of retirement age (60)
  - Table: name, department, current age, retirement date, countdown bar, urgency badge
  - Sorted by soonest retirement first
  - Accessible to HR, Director, Superuser via "Retirement Tracker" in sidebar
  - HR advice banner at bottom recommends 6-month advance planning
