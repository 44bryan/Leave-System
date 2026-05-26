# MICEI HRM — Project Document

## What Is This Application?

MICEI HRM is a web-based Leave Management System built for an Eye Hospital. It allows staff to submit leave requests digitally, which go through a two-stage approval process (Line Manager → HR Admin) before being fully approved. The system tracks leave balances automatically and gives each role a customized view of what concerns them.

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

### 2026-05-26 (Session 3) — Discipline permissions overhaul, sidebar badges, employee list & form improvements

- **Employee list — search & filter bar** (`accounts/views.py`, `accounts/templates/accounts/employee_list.html`)
  - Added name/ID search input, department dropdown, and role dropdown filters to the employee list
  - Server-side filtering via `Q(first_name__icontains) | Q(last_name__icontains) | Q(employee_id__icontains)`
  - Active/Former toggle moved inside the filter bar for cleaner layout
  - Empty state shows "No employees match your filters" with a clear link when filters are active

- **Employee form — searchable combobox** (`accounts/templates/accounts/employee_form.html`)
  - Line Manager / Supervisor and Unit Head selects replaced with searchable comboboxes
  - Pure JS (no external library): live-filter as you type, dropdown list, click to select
  - Native `<select>` hidden but still submitted with the form for full Django form compatibility
  - Clear/None option always shown at the top of the dropdown

- **Discipline permissions overhaul** (`discipline/models.py`, `discipline/views.py`, `discipline/urls.py`, all discipline templates)
  - New `is_proposal` + `proposal_note` fields on `DisciplineRecord` (migration `0004_add_is_proposal_flag`)
  - **HR / Superuser**: can formally issue all discipline types; proposals are NOT needed
  - **Admin Director / CEO**: can issue all types directly OR choose "Propose to HR" toggle
  - **Line Manager / Unit Head / Finance Director**: verbal warning only; always saved as a proposal to HR
  - Proposals are NOT visible to the target employee until HR formally executes them
  - New `execute_proposal` view (`/discipline/<pk>/execute/`) — HR converts a proposal to a formal notice
  - Detail page: proposals show a teal "Pending HR Execution" banner with "Execute" button for HR
  - Detail page: "proposal note" card visible to HR and the original submitter
  - List page: "Pending Proposals" section always shows above formal records (teal header)
  - List page: submitter stat cards simplified to "Executed Notices" + "Pending Proposals"
  - List page: name-search filter added (searches first/last name, privileged roles only)
  - Issue form: "Submit Proposal to HR" language for proposal-only roles; CEO/AD get a formal/propose toggle
  - Sidebar discipline section now only shows for HR, Admin Director, and Superuser (role-specific "Propose Discipline" links appear in manager/unit_head sections instead)
  - `is_director()` quirk (includes FD) handled explicitly — FD now correctly treated as proposal-only role
  - Context processor `notifications_ctx` updated to filter suspension check against `is_proposal=False` records

- **Sidebar badges** (`notifications/context_processors.py`, `templates/base.html`)
  - Context processor now injects `pending_leave_count` and `pending_discipline_proposals` for all templates
  - `pending_leave_count` = role-appropriate leave approval count (unit_head, manager, HR, director each get the right status)
  - `pending_discipline_proposals` = pending proposals count (HR and Admin Director only)
  - Badges added to: Unit Head Queue, Manager Queue, HR Approvals, Director Queue, Disciplinary Records
  - Unit Head and Manager sections now include a "Propose Discipline" shortcut link

- **Manager dashboard** (`dashboard/templates/dashboard/manager_dashboard.html`, `dashboard/views.py`)
  - Removed duplicate "My Leave Balance" KPI tile (already shown in `my_leave_section.html` at top of page)
  - Replaced with "Discipline Proposals" tile showing count of the manager's own pending proposals
  - "Issue Notice" topbar button renamed to "Propose Notice"

### 2026-05-26 (older) — Finishing pass: sidebar, appraisals popup, discipline list, leave entitlement, contracts

- **Discipline permissions overhaul** (`discipline/models.py`, `discipline/views.py`, `discipline/urls.py`, all discipline templates)
  - New `is_proposal` + `proposal_note` fields on `DisciplineRecord` (migration `0004_add_is_proposal_flag`)
  - **HR / Superuser**: can formally issue all discipline types; proposals are NOT needed
  - **Admin Director / CEO**: can issue all types directly OR choose "Propose to HR" toggle
  - **Line Manager / Unit Head / Finance Director**: verbal warning only; always saved as a proposal to HR
  - Proposals are NOT visible to the target employee until HR formally executes them
  - New `execute_proposal` view (`/discipline/<pk>/execute/`) — HR converts a proposal to a formal notice
  - Detail page: proposals show a teal "Pending HR Execution" banner with "Execute" button for HR
  - Detail page: "proposal note" card visible to HR and the original submitter
  - List page: "Pending Proposals" section always shows above formal records (teal header)
  - List page: submitter stat cards simplified to "Executed Notices" + "Pending Proposals"
  - List page: name-search filter added (searches first/last name, privileged roles only)
  - Issue form: "Submit Proposal to HR" language for proposal-only roles; CEO/AD get a formal/propose toggle
  - Sidebar discipline section now only shows for HR, Admin Director, and Superuser (role-specific "Propose Discipline" links appear in manager/unit_head sections instead)
  - `is_director()` quirk (includes FD) handled explicitly — FD now correctly treated as proposal-only role
  - Context processor `notifications_ctx` updated to filter suspension check against `is_proposal=False` records

- **Sidebar badges** (`notifications/context_processors.py`, `templates/base.html`)
  - Context processor now injects `pending_leave_count` and `pending_discipline_proposals` for all templates
  - `pending_leave_count` = role-appropriate leave approval count (unit_head, manager, HR, director each get the right status)
  - `pending_discipline_proposals` = pending proposals count (HR and Admin Director only)
  - Badges added to: Unit Head Queue, Manager Queue, HR Approvals, Director Queue, Disciplinary Records
  - Unit Head and Manager sections now include a "Propose Discipline" shortcut link

- **Manager dashboard** (`dashboard/templates/dashboard/manager_dashboard.html`, `dashboard/views.py`)
  - Removed duplicate "My Leave Balance" KPI tile (already shown in `my_leave_section.html` at top of page)
  - Replaced with "Discipline Proposals" tile showing count of the manager's own pending proposals
  - "Issue Notice" topbar button renamed to "Propose Notice"

### 2026-05-26 — Finishing pass: sidebar, appraisals popup, discipline list, leave entitlement, contracts

- **Notifications tab moved** (`templates/base.html`)
  - Notifications sidebar link moved to right after Dashboard (was last item in Main section)
  - Now visible immediately for every role — the universally-standard position in HR apps

- **Appraisals pending card — dismissible** (`dashboard/templates/dashboard/includes/pending_appraisals.html`)
  - Added a × close button to the "Appraisals Requiring Your Action" card
  - Dismissal stored in `localStorage` keyed by `date + count` so the banner returns the next day or when a new item is added
  - Card auto-hides on load if already dismissed for today's count

- **Discipline records list — full visual redesign** (`discipline/templates/discipline/list.html`)
  - Added left-border severity colour strip per row (amber → orange → red → dark)
  - Replaced plain text badges with rich icon+text badges (colour-coded per type)
  - Added **Reason** column with 80-char truncated preview (full text in tooltip)
  - Removed always-empty "Suspension Period" column; suspension dates now shown below the badge when applicable
  - Added **Workflow** column showing current step: "Awaiting HR" / "Awaiting Director" / "Complete"
  - Improved empty state with descriptive message and filter-clear link
  - Manager stat cards now have coloured top border

- **Per-employee deductible leave entitlement** (`leaves/views.py`, `leaves/urls.py`, `dashboard/templates/dashboard/leave_tracker.html`)
  - New view `set_leave_entitlement` (POST, HR/superuser only) at `/leaves/set-entitlement/`
  - Leave Tracker now shows a pencil icon next to each employee's entitlement figure
  - Clicking opens a Bootstrap modal pre-filled with current days; admin can change and save
  - Creates `LeaveBalance` for that year if it doesn't exist yet; uses `update_fields` for efficiency
  - Success message confirms the change; redirects back to the same tracker page/filters

- **Contract list — visual improvements** (`contracts/templates/contracts/contract_list.html`)
  - Added left urgency colour strip per row (green CDI, teal active, amber expiring-60, red expiring-30/expired)
  - Start + End dates merged into one "Period" column (two lines)
  - Row background tinted amber (≤60 days) or red (≤30 days) for at-a-glance urgency
  - Employee sub-line now shows position (truncated)
  - Status badges now include icons
  - Improved empty state with filter-clear link

- **My Contract page — richer right column** (`contracts/templates/contracts/my_contract.html`)
  - CDI/CDD employees: "Years of Service" card replaced with "Service & Contract" 2-stat card (years + days-remaining side-by-side)
  - Added "My Profile" card showing position, department, line manager, staff category, age, years-to-retirement
  - Added "Quick Actions" card (Apply for Leave, My Leave History, My Profile)
  - Expiry warning banner shown inside the card when ≤60 days remaining

---



### 2026-04-29 — Responsive tables, noise color cleanup, and filter improvements

- **Responsive tables** (`templates/base.html` + 8 template files)
  - Added global CSS: `.table-responsive > .table { white-space: normal !important; }` — removes forced horizontal scroll on desktop; text wraps naturally at the table level
  - Added `@media (max-width: 992px)`: `.page-content { padding: 16px; }` (mobile padding) and `.th-opt, .td-opt { display: none !important; }` (optional column utility)
  - Fixed 8 tables: `all_leaves.html`, `my_requests.html`, `hr_approvals.html`, `manager_approvals.html`, `unit_head_approvals.html`, `director_approvals.html`, `employee_list.html`, `leave_tracker.html`
  - Each table: removed `min-width: 820–900px; white-space: nowrap` from `<table>` → set smaller `min-width: 480–580px`
  - Added `class="text-nowrap"` to date, period, status, action cells so they still never break mid-word
  - Columns hidden on tablet/mobile (`.th-opt`/`.td-opt`): Applied On, Reason, End Date (my_requests), Manager Approved By, HR Approved By, HR Date, Supervisor, Position, Balance Bar progress

- **Noise color cleanup — #05BFDB eliminated** (17 files total)
  - `#05BFDB` (off-brand bright cyan) replaced with `#2db4c3` (official brand teal) across all 17 HTML templates
  - Affected: avatar gradients, chart color palettes, KPI tile gradients, login page background
  - Zero `#05BFDB` remaining anywhere in the codebase

### 2026-04-28 — Desktop density pass, filter fixes, and my_requests filtering

- **Global desktop density** (`templates/base.html`)
  - Added `@media (min-width: 993px)` block: `body { font-size: 14px }`, navbar 60px, sidebar 240px, table padding 10px, buttons 7px, logo 46px in 60px bar
  - Intentionally used `body { font-size: 14px }` (not `html`) to avoid shrinking small rem values like `.6rem`

- **Dashboard cleanup** (`ceo_dashboard.html`, `director_dashboard.html`, `hr_dashboard.html`)
  - Removed duplicate `@keyframes pulse` blocks (moved to `base.html`)
  - Fixed all inline card-header styles → `class="card-header card-header-chart"`
  - CEO: removed duplicate `{% include 'contract_analytics.html' %}` (was inserted twice)
  - HR: added 4-tile Rate Indicators row (Approval Rate, % Staff on Leave, Absent Today, Decisions Made)
  - HR: `pipeline-steps-row` CSS with connecting line and hover lift
  - Director: added Workforce Analytics section with `dirDeptChart` and `dirTypeChart` horizontal bar charts

- **Filter fixes** (`leaves/templates/leaves/all_leaves.html`, `leaves/views.py`)
  - Fixed year dropdown bug: `{% if y|stringformat:"s" == year_filter %}` → `{% if y == year_filter %}` (both are ints; Python 3 strict equality was returning False)
  - Fixed page subtitle: `{{ year }}` → `{{ year_filter }}` (context key is `year_filter`)

- **Employee filter added to My Requests** (`leaves/templates/leaves/my_requests.html`, `leaves/views.py`)
  - `my_requests` view now reads `year` and `status` GET params, filters queryset by `start_date__year` and `status`
  - Template gained a compact Year + Status filter form with Filter and Clear buttons
  - Card header now shows year and record count badge

### 2026-04-26 — Phase 3: Comprehensive Power BI redesign across ALL dashboards

- **Gradient KPI tiles (`.pbi-kpi` CSS class)** added to all six role dashboards
  - Each tile uses a `linear-gradient(135deg, …)` background with brand colors: navy for staff totals, green for approved, amber for pending, red for rejected, purple for discipline/director, teal for personal balance
  - Conditional color: pipeline/action tiles switch to amber/teal when count > 0, grey when count = 0 — matches Power BI conditional formatting pattern
  - Hover lift effect (`transform: translateY(-3px)`, increased `box-shadow`) via CSS transition
  - Added to: `ceo_dashboard.html`, `director_dashboard.html`, `admin_dashboard.html`, `manager_dashboard.html`, `unit_head_dashboard.html`

- **Polar Area chart — Contract Mix** (`ceo_dashboard.html`, `director_dashboard.html`)
  - Replaced existing doughnut `contractMixChart` with `type: 'polarArea'`
  - Semi-transparent `rgba()` background colors with solid `borderColor`
  - `scales.r` axis with `ticks.backdropColor: 'transparent'` and `grid.color: '#eef2f7'`

- **Attendance Donut** — Present vs On Leave today added to three dashboards
  - `ceo_dashboard.html`: `attendanceChart` canvas + `id="ceoPresent"` display in new `col-lg-3` card; present count computed in JS as `Math.max(0, total - onLeave)`
  - `director_dashboard.html`: `dirAttendanceChart` + `dirPresent` display, same layout
  - `manager_dashboard.html`: `teamAttendanceChart` + `mgrPresent` display in Team Analytics row
  - All attendance donuts use `cutout: '72%'`, `legend.display: false`, green/red color scheme; fallback to grey on zero total

- **Radar Chart — Team Leave Usage** (`manager_dashboard.html`)
  - `type: 'radar'`, member names as labels, usage % as data
  - `pointBackgroundColor` mapped per-member: red ≥ 90 %, amber ≥ 70 %, teal otherwise — visual risk indicator
  - `scales.r` with `min: 0, max: 100, stepSize: 25`, percentage tick callback

- **Team Leave Mix Polar Area** (`manager_dashboard.html`)
  - `teamLeaveOutcomeChart`: polar area showing Approved / Rejected / Pending counts for the team
  - Placed in `col-lg-3` of the new Team Analytics row alongside radar and attendance donut

- **Pipeline Funnel Chart** (`hr_dashboard.html`)
  - Horizontal bar chart (`indexAxis: 'y'`) above the 4 pipeline KPI step cards
  - 4 bars: Step 1 Manager (amber), Step 2 Unit Head Done (cyan), Step 3 HR Review (teal), Step 4 Director (navy)
  - Simulates Power BI funnel visual; decreasing bar lengths show attrition through approval stages

- **Department Headcount Vertical Bar** (`admin_dashboard.html`)
  - `deptHeadcountChart`: vertical bar with per-department `emp_count`, multi-color bars (10-color palette cycling)
  - Full-width card inserted above existing analytics row
  - Data injected via `{% for d in departments %}` loops in template; `truncatechars:14` for label readability

- **Unit Head dashboard full chart treatment** (`unit_head_dashboard.html`)
  - Four new charts added: `myLeaveDonut` (personal usage), `unitAttendanceChart` (present vs on leave), `unitOverviewChart` (horizontal bar leave snapshot), `unitBalanceChart` (per-member usage bar above balance table)
  - Balance bars color-coded: green < 70 %, amber 70–89 %, red ≥ 90 %
  - `{% block extra_css %}` added with pulse animation; `{% block extra_js %}` added with Chart.js CDN + all four inits

- **Contract Analytics include** (`dashboard/includes/contract_analytics.html`)
  - "Staff Category Distribution" CSS progress bars → horizontal bar chart `staffCatChart`
  - "Contracts by Department" HTML table → grouped bar chart `contractDeptChart` (one dataset per contract type)
  - Inline Chart.js CDN `<script src>` + IIFE at bottom of include (renders inside `{% block content %}` without waiting for parent `{% block extra_js %}`)
  - Affects CEO, Director, HR, and Admin dashboards simultaneously

- **Power BI-style dashboard chart enhancements — Phase 2** — remaining dashboards and shared include fully charted
  - **Unit Head dashboard** (`unit_head_dashboard.html`): Added full chart treatment — My Leave Usage donut (`myLeaveDonut`), Unit Attendance Today donut (`unitAttendanceChart`, present vs on-leave computed in JS), Leave Usage Snapshot horizontal bar (`unitOverviewChart` in top row), and Leave Usage by Member horizontal bar (`unitBalanceChart`) above the balance table; bars color-coded green/amber/red; `{% block extra_css %}` added with pulse animation; `{% block extra_js %}` added with Chart.js CDN + all four chart inits
  - **Contract Analytics include** (`dashboard/includes/contract_analytics.html`): Replaced "Staff Category Distribution" CSS progress bars with a horizontal bar chart (`staffCatChart`, colored by category color); replaced "Contracts by Department" HTML table with a grouped bar chart (`contractDeptChart`, one dataset per contract type — CDI teal, CDD amber, Internship cyan, Residents purple); inline `<script>` with Chart.js CDN + IIFE at bottom of include so charts render inside `{% block content %}` without waiting for parent `{% block extra_js %}`; affects CEO, Director, HR, and Admin dashboards simultaneously
- **Power BI-style dashboard chart enhancements — Phase 1** (same session, earlier work)
  - **All dashboards**: Monthly leave trend chart upgraded from plain bar → gradient line chart with hover tooltips
  - **CEO dashboard** (`ceo_dashboard.html`): Replaced flat discipline summary cards with 3-donut analytics row — Leave Outcomes (Approved/Rejected/Pending), Discipline Overview (Warnings/Suspensions/Dismissals), Contract Mix (CDI/CDD/Intern/WACS)
  - **Director / Finance Director dashboard** (`director_dashboard.html`): Same 3-donut analytics row as CEO; Leave Outcomes uses `pending_director` ("Awaiting Final") instead of `pending_all`
  - **HR dashboard** (`hr_dashboard.html`): Added new analytics row inside sortable "analytics" block — Leave Type Distribution (horizontal bar from `type_stats`), Leave Status donut (Approved/Rejected/Pending HR/Pending Dir.), Contract Mix donut; replaced department progress bars with a stacked horizontal bar chart (`deptActivityChart`); monthly chart now line with gradient
  - **Admin dashboard** (`admin_dashboard.html`): "Staff by Role" card now includes a role distribution donut chart (`roleDonutChart`); Analytics section now has Department Activity stacked bar chart, Discipline donut, and Contract Mix donut; low-balance section reformatted as a responsive card grid; monthly chart now line with gradient
  - **Manager dashboard** (`manager_dashboard.html`): Added team leave usage horizontal bar chart (`teamBalanceChart`) above the balance table; bars color-coded green (< 70%), amber (70–89%), red (≥ 90%)
  - All donut charts use consistent Power BI-style palette: teal `#088395`, navy `#0A4D68`, green `#059669`, amber `#d97706`, red `#dc2626`, purple `#7c3aed`
  - `Chart.defaults.font.family = 'Plus Jakarta Sans'` set globally in each dashboard's extra_js block

### 2026-03-22

- **Noise color cleanup — 14 HTML templates** — Replaced all off-brand hex colors with the official brand palette across 14 Django templates. Mappings applied:
  - `#0284c7`, `#0891b2`, `#0ea5e9` → `#2db4c3` (brand teal)
  - `#4527a0`, `#3730a3`, `#8b5cf6`, `#7b1fa2` → `#0A4D68` (brand dark blue)
  - `#e65100`, `#e67e22`, `#f97316` → `#d97706` (amber warning)
  - `#047857`, `#128438`, `#4caf50` → `#059669` (green success)
  - Files updated: `issue_contract.html`, `notifications.html`, `issue_form.html`, `my_contract.html`, `request_form.html`, `leave_detail.html`, `director_dashboard.html`, `admin_settings.html`, `hr_dashboard.html`, `employee_history.html`, `employee_form.html`, `contract_detail.html`, `action_form.html`
  - `leave_print.html` had no noise colors (only brand colors already in use)

### 2026-03-20

- **PDF links audit** — Confirmed all templates (`my_requests.html`, `all_leaves.html`) already use `leaves:pdf_leave`. No old `leaves:print_leave` links found in templates.

- **Discipline notifications in `propose_sanction`** (`discipline/views.py`)
  - When HR submits a sanction proposal: all active Admin Directors are notified via `notify()` with the proposed action details
  - When Director submits their decision: all active HR staff are notified via `notify()` with the final sanction decision

- **Finance Director coverage banner** (`leaves/views.py`, `leaves/templates/leaves/director_approvals.html`)
  - `director_approvals` view now checks if any Admin Director has an active approved leave today (`admin_dir_on_leave`)
  - Passes `employee` and `admin_dir_on_leave` to template context
  - Template shows an info banner ("Covering for Admin Director") when Finance Director is logged in and Admin Director is on leave
  - Shows a warning banner ("Admin Director Active") when Finance Director is logged in but Admin Director is NOT on leave

- **Contract "Extend" vs "Renew" labeling** (`contracts/templates/contracts/contract_detail.html`)
  - HR Actions section heading: INTERN/WACS → "Extend Contract" (calendar-plus icon, info color); CDD/CDI → "Renew Contract"
  - Contract type badge in Contract Details section now correctly shows "Internship" and "WACS Residency" (was falling through to "CDD Fixed Term")
  - Added INTERN/WACS options to the contract type dropdown in the renew form
  - Added `internship_type` select field to the extend form (shown only for INTERN contracts)
  - Submit button: INTERN/WACS → "Extend & Notify Employee"; CDD/CDI → "Renew & Notify Employee"
  - History section heading: INTERN/WACS → "Extension History"; others → "Renewal History"

- **`renew_contract` view updated** (`contracts/views.py`)
  - Reads `internship_type` from POST data for INTERN contracts and saves it on the new contract
  - Notification title uses "Contract Extended" for INTERN/WACS, "Contract Renewed" for CDD/CDI
  - Success message uses "extended" / "renewed" appropriately
  - `_contract_renewal_message()` updated: INTERN → "extended", WACS → "extended", CDD/CDI → "renewed"

- **`my_contract.html` audit** — Already correctly shows "Internship Contract", "WACS Residency / Trainee Programme", internship_type display, and separate programme info cards. No changes needed.

### 2026-03-19 (update)

- **PDF fixes: signatures + logo colors + unit-head fallback** (`leaves/pdf_utils.py`)
  - Fixed signatures not rendering: changed `mask='auto'` → `mask=None` in `cv.drawImage()` since PIL already composites images to RGB (no alpha channel)
  - Updated color palette to match the Magrabi logo (`#31b8cf` cyan, `#2496ba` blue): section bars use dark teal `#0d5c6f`, approval cell headers use logo cyan `#31b8cf` with dark text
  - Unit Head fallback: if `leave.unit_head_action_by` is None, the Line Manager's info and signature appear in the Unit Head cell (since the Line Manager acts as Unit Head in that case)
  - Employee requestor signature given larger display area (42% width, 18 mm tall)
  - Approval grid cells enlarged to 35 mm tall for more signature space

### 2026-03-19

- **Leave authorisation PDF — complete professional redesign** (`leaves/pdf_utils.py`)
  - Old design: paper-form style with blank lines to write on, cramped approval table
  - New design: modern, bilingual (English/French) layout for Magrabi Cameroon Eye Institute
  - Dark teal top accent bar + logo + bilingual title ("AUTORISATION D'ABSENCE / LEAVE AUTHORISATION") + reference number header
  - Teal section header bars for each section (white bold label)
  - Label-over-value info cells with alternating row backgrounds (white / light grey)
  - Sections: Employee Information · Leave Details · Reason for Leave · Requestor Declaration · Approvals
  - **Requestor Declaration row**: employee name (left) + signature image (centre) + date (right)
  - **Approvals 2×2 grid**: Unit Head + Line Manager (top row) | HR + Director (bottom row); each cell has teal header, approver name, action date, and embedded signature image
  - Professional footer with teal rule, system name, and auto-generated date
  - `_load_sig()` uses PIL to composite transparent PNGs onto white before embedding via ReportLab `ImageReader`
  - New helpers: `frect()`, `section_bar()`, `info_row()`, `draw_sig()`, colour palette constants

---

### 2026-03-18

- **Draw-pad digital signatures on approval forms**
  - Removed file-upload signature from employee profile page and employee edit form entirely
  - All 4 approval forms (Unit Head, Line Manager, HR, Director) now include a canvas signature drawing pad (`signature_pad` JS library via CDN)
  - Pad appears only when "Approve" is selected; hidden when "Reject" is selected
  - Submit is blocked client-side if the approver hasn't drawn a signature
  - On approve, the drawn PNG is saved to `employee.signature` and used on all future leave PDFs for that approver
  - `_save_drawn_signature()` helper added to `leaves/views.py`
  - Removed `upload_signature` view from `accounts/views.py` and URL from `accounts/urls.py`

- **Admin signature management** — superuser can pre-set a signature for any employee
  - Draw pad panel added to the employee edit form, visible to superusers only (`{% if employee and request.user.is_superuser %}`)
  - Shows current signature on file (if any) alongside the draw pad
  - New view `set_employee_signature` in `accounts/views.py` (POST, superuser-only)
  - New URL: `accounts/employees/<pk>/set-signature/`

- **Signature preview on leave detail page** (`leaves/leave_detail.html`)
  - Each approver step in the Approval History timeline now shows the approver's signature image if one is on file
  - Covers: Unit Head, Manager, HR, Director steps

---

### 2026-03-17

- **Suspension lockout — phone/tablet fix** (`templates/base.html`)
  - When suspended, the page content is now **fully replaced** by a clean "Account Suspended" card instead of showing the normal page. Eliminates any risk of accessing actions on mobile/tablet.
  - The suspension card shows only two buttons: "View Notifications" and "Sign Out".
  - The red suspension banner wraps correctly on small screens and includes an inline "Sign Out" button.
  - Suspension JS now sweeps ALL `<a>`, `<button>`, and `<input[type=submit]>` elements on the page and removes `href` attributes so mobile long-press cannot navigate either.
  - `data-no-suspend` added to: notification bell, each notification item link, "View All Notifications", both suspension card buttons.

### 2026-03-16

- **New Employee fields** — `sex` (M/F), `nationality`, `contract_number`, `qualifications` added to `Employee` model
  - Migrations 0007 and 0008 applied
  - Both `EmployeeCreateForm` and `EmployeeEditForm` updated to include all new fields
  - `Add Employee` / `Edit Employee` form template fully reorganised: Personal Info section (sex, DOB, nationality), Employment Details section

- **New Roles** — `intern` and `wacs_resident` added to `Employee.ROLE_CHOICES`
  - Badge colors: Intern = info (teal), WACS Resident = warning (amber)

- **Smart contract-type form behaviour** (`accounts/employee_form.html`)
  - Selecting **Internship (INTERN)**: optional employment fields (position, department, staff category, supervisor, date joined, qualifications, contract number) are grayed out and pointer-events disabled; a warning banner explains that only Name, Employee ID, Email, Phone and DOB are required; Role auto-set to `intern`
  - Selecting **WACS**: full employee account, all fields optional; Role auto-set to `wacs_resident`
  - Selecting **CDI**: end date grayed out (not required)
  - Switching away from INTERN/WACS: Role resets to `employee`

- **Dashboard — INTERN/WACS stat cards** (`dashboard/templates/dashboard/includes/contract_analytics.html`)
  - Contract KPI strip now shows **Interns** and **WACS Residents** stat cards (linking to filtered contracts list)
  - `_build_contract_analytics()` in `dashboard/views.py` now returns `contract_total_intern` and `contract_total_wacs`

- **Excel Bulk Import** — HR and Admin can upload an Excel file to create employees in bulk
  - URL: `/accounts/employees/import/`
  - Sidebar link under "Employees → Import from Excel" (visible to HR and superuser)
  - **Download Template** button generates a pre-formatted `.xlsx` with all column headers; required columns in red, optional in teal; includes a Notes sheet explaining valid values
  - Upload processes each row: validates required fields, checks for duplicate employee IDs/emails, looks up departments by name, creates User + Employee + Contract + LeaveBalance + welcome notification in a single transaction
  - Results page shows Created/Skipped counts and per-row error details
  - Dependency: `openpyxl==3.1.5` added to `requirements.txt`

  **Excel column headers (exact match, case-insensitive):**
  | Column | Required? |
  |--------|-----------|
  | `first_name` | Yes |
  | `last_name` | Yes |
  | `email` | Yes |
  | `employee_id` | Yes |
  | `contract_type` | Yes (CDI/CDD/INTERN/WACS) |
  | `contract_start_date` | Yes |
  | `contract_end_date` | Required for CDD/INTERN/WACS |
  | `date_of_birth` | Optional |
  | `sex` | Optional (M/F) |
  | `nationality` | Optional |
  | `phone` | Optional |
  | `position` | Optional |
  | `department` | Optional (must match existing dept name) |
  | `role` | Optional (auto-set from contract type) |
  | `staff_category` | Optional |
  | `date_joined_hospital` | Optional |
  | `qualifications` | Optional |
  | `contract_number` | Optional |



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

- **Dismissal & Suspension enforcement**
  - `Employee.dismissal_date` (DateField, nullable) added to `accounts/Employee` model — migration `0006` applied
  - When a `dismissal` discipline notice is issued, `dismissal_date` is stamped on the employee record
  - `_process_pending_dismissals()` in `discipline/views.py` auto-deactivates dismissed employee Django User accounts 14 days after `dismissal_date`; called at the start of `discipline_list`
  - `notifications/context_processors.py` now queries active suspensions and injects `is_suspended` (bool) and `suspension_end` (date) into every template
  - `base.html` suspension banner: sticky red bar shown to suspended employees with suspension end date
  - `base.html` suspension JS: greys out all nav links and disables form submit buttons while suspended
  - `.suspension-overlay` CSS class added to `base.html` style block

- **Notification URL fix** — all 7 `notify()` calls in `leaves/views.py` now use `reverse()` instead of hardcoded strings; `from django.urls import reverse` import added

- **HR Employee List — Former Employees toggle**
  - `accounts/views.py` `employee_list` now accepts `?show_former=1` GET param
  - When `show_former=1`, lists `is_active=False` employees; default lists `is_active=True`
  - `show_former` boolean passed to template context for toggle button rendering

### 2026-03-15 (session 2 — continued)

- **Suspension UI fixes**
  - Notification bell + logout buttons excluded from suspension greying via `data-no-suspend` attribute
  - Notification dropdown z-index fix: topbar raised to `z-index:1050` so dropdown appears above red suspension banner
  - Suspension banner removed from sticky positioning (now flows with content); topbar `top` set to `76px` to sit below fixed logo-bar

- **Staff category — numeric format**
  - `Employee.staff_category` changed from letter-based choices (A–L) to free-text numeric format `1–12` with optional letter suffixes (e.g. `12AB`, `12AL`)
  - `RegexValidator` enforces pattern `^(?:[1-9]|1[0-2])[A-Z]{0,3}$`
  - `staff_category` max_length increased from 3 to 6; `choices` removed
  - Both `EmployeeCreateForm` and `EmployeeEditForm` updated: TextInput with uppercase styling + `clean_staff_category()` method
  - Migration `accounts/migrations/0009_staff_category_numeric.py` applied

- **Seniority removed entirely**
  - All seniority properties, badges, cards, and references removed from `contracts/models.py`, `contracts/views.py`, and all contract templates (`contract_detail.html`, `contract_list.html`, `my_contract.html`, `stats.html`)
  - Admin and contract analytics dashboards updated to remove seniority badges
  - Replaced with plain "Years of Service" display everywhere

- **Username auto-generation improved**
  - `_generate_username()` now uses `firstname.lastname` format
  - On collision, appends sequential number (`firstname.lastname2`, `firstname.lastname3`, etc.)
  - `username_suggest` API and `employee_create` view updated to accept `last_name` parameter
  - Employee form JS updated to send both first and last name to suggest endpoint

- **Excel import restricted to superuser only**
  - `employee_import` view now requires `request.user.is_superuser` (was `@hr_or_superuser_required`)
  - Sidebar link moved from HR block to superuser-only block in `base.html`

- **Duplicate Retirement Tracker removed**
  - Removed duplicate Retirement Tracker sidebar link from HR section in `base.html`

- **Sidebar scroll position persistence**
  - `sessionStorage` used to save/restore sidebar scroll position across page navigations
  - JS added to `base.html` before the Live Search section

- **Topbar always visible on scroll**
  - Logo-bar: `position:fixed; top:0; height:76px; z-index:1100`
  - Topbar: `position:sticky; top:76px; z-index:1050` — sticks below the logo-bar on all devices

- **Discipline module enhancements**
  - Line Manager HR notification: when a manager issues a verbal warning, all HR staff receive an in-app notification with a link to the record
  - Delete discipline record: Admin Director and superuser can permanently delete a record (as if it never happened); dismissal records also clear `employee.dismissal_date`; URL: `discipline/<id>/delete/`
  - Sequential workflow: Step 3 (Director's Proposal) only appears in detail view after Step 2 (HR Proposal) is complete — eliminates dual "Accept" buttons
  - Manager scope: Line Managers now see ONLY records they personally issued (filter: `issued_by=request.user`)
  - Manager success rate panel: discipline list shows 3 stat cards for managers (Notices Issued / Director Reviewed / No Further Action)
  - Privileged view (all records): Admin Director, Finance Director, HR, CEO, Superuser see all records
  - Discipline list table: "Issued By" and "Department" columns only shown to privileged users; "Director's Decision" column shown to managers with live status

### 2026-03-16

- **Dashboard KeyError fix** — `_build_contract_analytics` dept_map and `contract_stats` dept_map changed from `{'CDI':0,'CDD':0}` to `defaultdict(int)` to handle INTERN/WACS contract types without KeyError

- **Contract notifications — type-specific messages**
  - `contracts/views.py`: added `_contract_issue_message()`, `_contract_renewal_message()`, `_contract_termination_message()` helpers
  - INTERN → "Internship Contract Issued/Renewed"; WACS → "WACS Residency Contract Issued/Renewed"; CDI → "Permanent (CDI)"; CDD → "Fixed-Term (CDD)"
  - End-date validation now covers INTERN and WACS (not only CDD)
  - `accounts/views.py` welcome notification also uses type-specific message

- **Staff category distribution — numeric system**
  - `_build_contract_analytics()` in `dashboard/views.py` rewritten: queries actual assigned categories dynamically, groups into Category 1–6 and Category 7–12 (instead of old A-L/AA-AL/BA-BL letter system)
  - `staff_category_detail` now shows all real assigned values (e.g. 5, 12A, 12AB) with badge colors

- **Department breakdown — INTERN & WACS columns**
  - All three department breakdown tables (contract_analytics.html, admin_dashboard.html, contracts/stats.html) updated to show CDI / CDD / Intern / WACS / Total columns (removed misleading CDD % bar)

- **Intern accounts — simplified experience**
  - "My Discipline Record" sidebar link hidden from interns (`{% if not user.employee.is_intern %}`)
  - Leave submission: interns bypass manager approval — leave auto-advances to `manager_approved` on submission, HR notified directly with "[Intern Leave Request]" label
  - Admins (CEO, Finance Director, Admin Director, System Admin, Superuser) can still see all intern data

### 2026-03-17

- **Intern registration fields** — `school_name` and `speciality` added to `Employee` model (migration `0010_add_intern_school_speciality`)
  - Both `EmployeeCreateForm` and `EmployeeEditForm` include the new fields in `fields` list and `widgets` dict
  - `employee_form.html`: new "Internship Details" section (`#intern-fields-section`) shown/hidden via JS when INTERN contract type OR intern role is selected

- **Internship type** — `internship_type` field added to `Contract` model (migration `0004_add_internship_type`)
  - Choices: Academic / Professional / Vocational / Observation / Other
  - `issue_contract.html` now has all 4 contract type radios (CDD / CDI / INTERN / WACS) with tinted cards; internship_type dropdown appears only when INTERN is selected
  - `contracts/views.py` `issue_contract` saves `internship_type` from POST when contract_type == 'INTERN'
  - `my_contract.html` shows internship type, school, and speciality in the intern info card

- **Auto-deactivate expired interns/WACS** — `_process_expired_interns()` in `dashboard/views.py`
  - On every dashboard page load: finds active INTERN/WACS contracts with `end_date < today`, marks them `expired`, deactivates the user account (`is_active=False`)
  - Same behavior as dismissed employees — account preserved, just deactivated; HR can still view stats

- **French i18n** — full translation infrastructure enabled
  - `USE_I18N = True`, `LocaleMiddleware` added to MIDDLEWARE (after SessionMiddleware)
  - `LANGUAGES = [('en', 'English'), ('fr', 'Français')]`
  - `LOCALE_PATHS = [BASE_DIR / 'locale']`
  - `locale/fr/LC_MESSAGES/django.po` — comprehensive French translations for all key UI strings
  - Language switcher (EN / FR buttons) added to settings dropdown in topbar
  - `path('i18n/', include('django.conf.urls.i18n'))` added to `urls.py` for `set_language` endpoint
  - **Note:** On Railway (Linux), `python manage.py compilemessages` runs automatically; locally requires GNU gettext (`msgfmt`) to be installed

### 2026-03-20 — Full French i18n pass: all templates translated

- **Comprehensive `{% trans %}` / `{% blocktrans %}` tagging across all 16 templates**
  - Every user-visible English string now wrapped for translation
  - Templates updated: `base.html`, `admin_dashboard.html`, `hr_dashboard.html`, `director_dashboard.html`, `employee_dashboard.html`, `unit_head_dashboard.html`, `request_form.html`, `my_requests.html`, `action_form.html`, `leave_detail.html`, `all_leaves.html`, `profile.html`, `employee_list.html`, `employee_form.html`
  - Strings containing template variables use `{% blocktrans with var=value %}` (e.g. birthday banner, welcome subtitle, on-leave alert, discipline KPI years, upcoming-birthday count)
  - HTML-embedded variable strings (on-leave alert with `<strong>` tags) also use `{% blocktrans %}`

- **`locale/fr/LC_MESSAGES/django.po` — ~100+ new msgid/msgstr pairs added**
  - Covers: admin dashboard labels, director dashboard labels, HR discipline strip, sidebar section labels, sidebar nav links (Birthday Calendar, Director Queue, All Requests, CEO Overview, Discipline / Contracts / Admin sections), suspension banner, signature pad strings, birthday messages, contract analytics labels, profile page fields

- **`locale/fr/LC_MESSAGES/django.mo` compiled via Python script**
  - GNU gettext not installed locally; `.mo` file compiled using a pure-Python MO generator
  - Django confirmed loading 330 translated messages from the `.mo` file
  - UTF-8 accented characters verified correct in memory (`é`, `è`, `à`, `ô`, etc.)

### 2026-03-20 — Personal leave section added to all role dashboards

- **All role dashboards now show personal leave info at the top**
  - HR, Director, Manager, and Admin users are also employees — they need to see their own leave balance and apply for leave just like regular staff
  - Created shared include: `dashboard/templates/dashboard/includes/my_leave_section.html`
    - Shows birthday banner, suspension alert, on-leave alert
    - Shows deductible balance card (gradient), non-deductible leaves card, pending count + apply button card
    - Shows "My Recent Leave Requests" table with link to full history
    - Uses `my_pending_count`, `my_recent_requests`, `balance`, `on_leave`, `active_suspension`, `is_own_birthday`, `today`, `employee`
  - **`dashboard/views.py` updated:**
    - `hr_dashboard`: adds personal leave context (`my_balance`, `my_recent_requests`, `my_pending_count`, `my_on_leave`, `my_active_suspension`, `my_is_birthday`)
    - `director_dashboard`: same additions
    - `manager_dashboard`: same additions (also imports DisciplineRecord)
    - `admin_dashboard`: tries `get_employee(request)` — if admin has an employee profile, computes all personal context; if not, passes `None` and template skips the section
  - **Templates updated:** `hr_dashboard.html`, `director_dashboard.html`, `manager_dashboard.html` now include `my_leave_section.html` at the top of content block
  - Admin template wraps the include in `{% if employee and balance %}` guard (superuser may not have an employee profile)

### 2026-03-20 — Discipline notifications, finance director coverage, contract extend/renew labels

- **Discipline notification chain fully wired** (`discipline/views.py`)
  - Manager issues verbal warning → employee notified + all HR staff notified (already existed)
  - HR submits sanction proposal (`propose_sanction`) → all active Admin Directors notified with proposed action
  - Director submits final decision (`propose_sanction`) → all active HR staff notified with final decision
  - Full chain: Manager → HR → Director → HR (notifications complete for every step)

- **Full leave approval notification audit** (`leaves/views.py`)
  - Confirmed all 5 approval steps notify both the employee AND the next approver:
    1. Submit → unit head / line manager notified
    2. Unit Head approves → employee + line manager notified
    3. Manager approves → employee + all HR notified
    4. HR approves → employee + all Admin Directors + Finance Directors notified
    5. Director approves → employee notified
  - All rejection steps also notify the employee

- **Finance Director coverage banners** (`leaves/views.py`, `leaves/templates/leaves/director_approvals.html`)
  - `director_approvals` view detects if any Admin Director has an active approved leave today (`admin_dir_on_leave`)
  - Template shows an info banner to Finance Director when Admin Director is on leave ("Covering for Admin Director")
  - Shows a warning banner when Finance Director is logged in but Admin Director is NOT on leave

- **Contract "Extend" vs "Renew" labeling** (`contracts/templates/contracts/contract_detail.html`, `contracts/views.py`)
  - INTERN/WACS: heading shows "Extend Contract", button shows "Extend & Notify Employee", history shows "Extension History"
  - CDD/CDI: heading shows "Renew Contract", button shows "Renew & Notify Employee", history shows "Renewal History"
  - Contract type badge now correctly shows "Internship" and "WACS Residency" (no longer falls through to "CDD Fixed Term")
  - `internship_type` select field added to the extend form (visible for INTERN contracts only)
  - `renew_contract` view saves `internship_type` from POST when `contract_type == 'INTERN'`
  - `_contract_renewal_message()` uses "extended" for INTERN/WACS, "renewed" for CDD/CDI

### 2026-03-20 — Employee history view, super admin role, full French translation pass

- **Employee History / Audit View** (`accounts/views.py`, `accounts/templates/accounts/employee_history.html`)
  - New URL: `/accounts/employees/<pk>/history/` (name: `accounts:employee_history`)
  - Access: HR, Admin Director, Finance Director, CEO, Superuser only
  - Shows 4 tabbed sections: Profile · Contracts · Leave History · Discipline
  - Profile tab: personal info + employment details + current year leave balance card
  - Contracts tab: full contract history with type badge, dates, status, notes — links to contract detail
  - Leave History tab: all leave requests with type, period, days, status — links to leave detail
  - Discipline tab: all discipline records with type, reason, HR proposal, Director decision — links to discipline detail
  - Employee names are now **clickable links** in: Employee List, All Requests (leaves), Contracts List, Discipline List

- **Super Admin role** (`accounts/models.py`)
  - Added `('super_admin', 'System Administrator')` to `ROLE_CHOICES`
  - `get_role_display_badge()` always returns `'dark'` for Django superusers (`user.is_superuser`)
  - New method `get_effective_role_display()`: returns `'System Administrator'` for superusers, otherwise normal role display
  - `employee_list.html` and `employee_history.html` use `get_effective_role_display` instead of `get_role_display`

- **French translation — comprehensive pass** (`locale/fr/LC_MESSAGES/django.po`, `.mo`)
  - Added ~200 new msgid/msgstr pairs covering:
    - Profile page: Category, Sex (Male/Female), all field labels, change password form
    - Employee history template: all tab labels, table headers, status labels
    - Role names: System Administrator, Administration Director, Finance Director, HR Admin, etc.
    - Contract list: all filter/stat labels, table headers
    - Discipline list: all action strings, filter labels
    - Leave list: all table headers, filter labels
    - Common UI: Active/Inactive, Filter, Clear, Pending, View, Notes, etc.
  - Profile template fix: `Category` now wrapped in `{% trans %}`, sex display uses `{% trans employee.get_sex_display %}`
  - Total: 395 messages compiled to `.mo`

- **Appraisal: full score audit chain + signature PNG fix** (2026-04-29)
  - **Signature PNG fix**: `appraisals/pdf_utils.py` — replaced `_load_sig` with a Pillow-first implementation (mirrors leave PDF's `_load_sig_b64`). Always composites RGBA→RGB on white before handing to ReportLab. Previously `ImageReader` silently accepted RGBA but `drawImage` failed; now Pillow handles all modes. Also added `flattenToRgbPng()` in `_sig_js.html` and `employee_fill.html` so future signatures are stored as RGB PNG from the browser.
  - **Per-role score snapshots**: Added `hr_score_changes`, `director_score_changes`, `ceo_score_changes` JSONField to `AppraisalRecord` (migration `0005`). Each stores `{fname: value}` for only the fields that role actually changed. `_apply_score_override` now saves per-role snapshots alongside the running `override_*` fields.
  - **Model method `score_changes_display()`**: Returns list of dicts `{label, supervisor, hr, director, ceo, final}` for every field where any role changed a score — used by both templates and PDF.
  - **Web review pages**: `_prior_hr.html` shows a diff table (Factor / Supervisor / HR Modified) when HR changed scores. `_prior_director.html` shows (Factor / Before / Director Modified). CEO's fill page sees both tables via the included partials.
  - **PDF audit table**: `override_diff_table()` now shows dynamic columns — only the roles that made changes appear. Columns: Factor | Supervisor | [HR] | [Director] | [CEO] | Final. Footer line attributes each modification with name and date.

- **Appraisal PDF + signatures + score tracking + co-worker section** (2026-04-29)
  - **`appraisals/templates/appraisals/_sig_js.html`** and **`employee_fill.html`**: Added `flattenToRgbPng()` — composites signature canvas onto a white background before encoding as PNG. This ensures the stored data URI is always RGB (not RGBA), which ReportLab's `ImageReader` can render directly without Pillow. Previously RGBA transparent PNGs failed to render, causing "(not signed)" to appear.
  - **`appraisals/pdf_utils.py`**: Added `override_diff_table(field_labels)` method — renders an amber-header comparison table showing each factor where the score differs from the supervisor's original, listing the final value and attributing each role (HR / Director / CEO) that made changes. Called after Section 4 in `generate_appraisal_pdf`. Section 4 bar label updated to "(Original Scores)". `_render_sig` helper now handles both image rendering and italic-name fallback.
  - **Co-worker reviews embedded on My Appraisals page** (`my_appraisals.html` + `my_appraisals` view): Removed standalone sidebar link for "Co-Worker Reviews". The `my_appraisals` view now passes `coworker_pending` (STATUS_COWORKER) and `coworker_submitted` (STATUS_UNIT_HEAD, editable) to the template. Two sections appear above the history table: a blue "awaiting comment" section and a grey "submitted (editable)" list. "My Appraisals" sidebar link now shows a red badge for `pending_coworker_count`.

- **Appraisal score override audit, PDF signatures, HR false-positive fix** (2026-04-29)
  - **`appraisals/models.py`**: Added 6 per-role score-modification tracking fields: `score_modified_by_hr / at_hr`, `score_modified_by_director / at_director`, `score_modified_by_ceo / at_ceo` (FK to Employee, null=True). Migration `0004_per_role_score_modification_tracking` created and applied.
  - **`appraisals/views.py` — `_apply_score_override`**: Fixed false positive — now compares each submitted value against `mgr_{fname}`; only marks `changed=True` if the value actually differs from the supervisor's score. Accepts new `role` kwarg ('hr'/'director'/'ceo') and sets the corresponding per-role fields when changed. Updated `hr_fill`, `director_fill`, `ceo_fill` calls to pass `role=`.
  - **`appraisals/templates/appraisals/_prior_hr.html`**: Changed `score_override_by == hr_signed_by` condition to `score_modified_by_hr` direct field check — eliminates false "HR modified scores" alert.
  - **`appraisals/templates/appraisals/_prior_director.html`**: Same — now uses `score_modified_by_director`.
  - **`appraisals/pdf_utils.py`**: Added `_render_sig(sig_b64, signed_by, ...)` helper on Builder — tries image first, falls back to italic name in BLUE when image is empty/fails, only shows "(not signed)" if `signed_by` is None. Updated `sig_strip` and `comment_block` to call `_render_sig` instead of inline `if sig_b64` logic.

- **Appraisal re-editing, sidebar co-worker link, live search dropdown** (2026-04-29)
  - **`appraisals/views.py` — employee_fill**: Changed blocking condition from `status != STATUS_EMPLOYEE` to allow `STATUS_COWORKER` and `STATUS_UNIT_HEAD`. Initial submit advances status and notifies coworker as before. Re-edit when `STATUS_COWORKER` saves fields and updates coworker assignment (notifies new coworker if changed). Re-edit when `STATUS_UNIT_HEAD` saves employee fields only, status stays unchanged.
  - **`appraisals/views.py` — coworker_fill**: Changed blocking condition to allow `STATUS_COWORKER` or `STATUS_UNIT_HEAD`. Initial submit (STATUS_COWORKER) advances to STATUS_UNIT_HEAD and notifies unit head. Re-edit (STATUS_UNIT_HEAD) saves comment/signature, keeps status, no re-notification.
  - **`notifications/context_processors.py`**: Added `pending_coworker_count` (count of AppraisalRecords where `coworker_signed_by=emp` and `status=STATUS_COWORKER`) injected into every template.
  - **`templates/base.html`**: Added "Co-Worker Reviews" nav link (with red badge for `pending_coworker_count`) to the general employee section (after "My Appraisals"), visible to all non-superuser employees. Removed duplicate link from unit_head-only section.
  - **`appraisals/templates/appraisals/employee_fill.html`**: Coworker `<select>` now has `size="6"` (visible list, no dropdown), live search input above it filters options as user types. Pre-selects current coworker on re-edit via `{% if record.coworker_signed_by ... %}selected{% endif %}`.

- **Power BI analytics amplification — CEO, Director, HR dashboards** (2026-04-28)
  - **New context variables** added to `views.py` for all three views: `dept_stats` (approved requests per department, year-filtered), `type_stats` (approved requests per leave type, year-filtered), `on_leave_count` (int count, avoids re-calling `.count()`), `approval_rate` (integer %, zero-division guarded), `on_leave_pct` (integer %, zero-division guarded).
  - **CEO dashboard** (`ceo_dashboard.html`): Added 4-tile "Org Health Rate Indicators" row (Approval Rate %, Staff on Leave %, Absent Today, Decisions Made) with colored left-border KPI cards. Added "Workforce Analytics" section with 2 Power BI-style horizontal bar charts — `ceoDeptChart` (approved leave by department) and `ceoTypeChart` (approved leave by type), both using `indexAxis: 'y'` with IIFE pattern and empty-state fallback. Added missing `{% include 'dashboard/includes/contract_analytics.html' %}`.
  - **Director dashboard** (`director_dashboard.html`): Same 4-tile rate indicators row (Approval Rate %, Staff on Leave %, Absent Today, Awaiting Your Signature). Added "Workforce Analytics" section with `dirDeptChart` + `dirTypeChart` horizontal bar charts. Fixed 3 donut card headers: `style="background:#f8fbfd;..."` → `class="card-header card-header-chart"`. Removed duplicate `@keyframes pulse`.
  - **HR dashboard** (`hr_dashboard.html`): Added "Rate Indicators" 4-tile row inside overview block using existing `.hr-kpi-card` style (Approval Rate %, % Staff on Leave, Absent Today count, Decisions Made). Fixed 7 card headers to `card-header-chart`, 1 to `card-header-chart d-flex ...`. Removed duplicate `@keyframes pulse`.

- **Frontend audit — 7 improvements** (2026-04-28)
  - **Chart.js deduplication**: Moved CDN load + `Chart.defaults` to `base.html` before `{% block extra_js %}`. Removed duplicate `<script src="chart.js">` lines from all 7 dashboard templates. `contract_analytics.html` keeps its own load intentionally (renders in `{% block content %}` before base.html scripts execute).
  - **Mobile table responsiveness**: Added `min-width` + `white-space: nowrap` to all multi-column tables (`all_leaves.html`, `manager_approvals.html`, `hr_approvals.html`, `director_approvals.html`, `unit_head_approvals.html`, `my_requests.html`). Removed redundant inline overflow styles from `employee_list.html`'s `table-responsive` wrapper (Bootstrap already handles it).
  - **Form error display**: Replaced `{{ form.field.errors.0 }}` (first error only) with `{% for error in form.field.errors %}` loop in `request_form.html` and `employee_form.html` — all validation messages now show.
  - **Empty states**: Verified all tables have `{% empty %}` states — `all_leaves.html`, `my_requests.html`, `employee_leave_summary.html`, all approval pages already had them.
  - **Card header CSS utility classes**: Added to `base.html`: `.card-header-sm` (0.82rem), `.card-header-chart` (#f8fbfd bg), `.card-header-green` (#f0fdf4 bg), `.card-header-blue` (#f0fafc bg), `.t-xs`/`.t-sm`/`.t-secondary` text helpers. Replaced inline `style="..."` on all card headers across 7+ templates.
  - **Active nav state**: Confirmed JS already strips query strings — `window.location.pathname` excludes QS, `href.split('?')[0]` handles QS on hrefs. No change needed.
  - **Inline style reduction**: Moved `.pending-pulse` + `@keyframes pulse` to `base.html`; removed 4 duplicate template-local definitions. Replaced 40+ `style="font-size:0.72rem;color:#6b7a8d;"` inline styles with `class="t-secondary"` and `style="font-size:0.82rem;"` with `class="t-sm"` across approval and listing templates.

- **Brand color system applied across 14 templates** (2026-03-22)
  - Replaced legacy blue/purple/orange UI chrome colors with brand palette across all listed templates:
    - `#0284c7` → `#2db4c3` (brand teal)
    - `#0891b2` → `#2db4c3` (brand teal)
    - `#7c3aed` → `#2db4c3` (brand teal)
    - `#4527a0` → `#0A4D68` (brand navy)
    - `#1d4ed8` → `#2db4c3` (brand teal)
    - `#ea580c` → `#2db4c3` (brand teal)
    - `#15803d` → `#1a8fa0` (brand teal-dark)
    - `#16a34a` → `#2db4c3` (UI chrome instances only, not semantic status badges)
  - Files updated: `admin_dashboard.html`, `director_dashboard.html`, `hr_dashboard.html`, `retirement_dashboard.html`, `includes/contract_analytics.html`, `contracts/stats.html`, `contracts/my_contract.html`, `contracts/contract_list.html`, `accounts/profile.html`, `accounts/employee_form.html`, `accounts/employee_history.html`, `accounts/employee_excel_results.html`, `discipline/detail.html`, `leaves/leave_type_list.html`
  - Semantic status colors (`#059669`, `#d97706`, `#dc2626`, `#10b981`, `#ef4444`, `#f59e0b`) were preserved

