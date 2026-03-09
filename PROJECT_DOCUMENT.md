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
