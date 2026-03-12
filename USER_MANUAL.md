# LeaveDesk — User Manual
### Magrabi ICO Cameroon Eye Institute
---

## Table of Contents
1. [Getting Started](#1-getting-started)
2. [User Roles](#2-user-roles)
3. [Employee Guide](#3-employee-guide)
4. [Line Manager Guide](#4-line-manager-guide)
5. [HR Admin Guide](#5-hr-admin-guide)
6. [Administration Director Guide](#6-administration-director-guide)
7. [System Admin Guide](#7-system-admin-guide)
8. [Leave Types Reference](#8-leave-types-reference)
9. [Working Days Policy](#9-working-days-policy)

---

## 1. Getting Started

### Logging In
1. Open your browser and go to the LeaveDesk URL.
2. Enter your **Username** and **Password**.
3. Click **Sign In**.
4. You will be taken to your dashboard based on your role.

### First Login (Admin Account)
After a factory reset, the admin account credentials are:
- **Username:** `admin`
- **Password:** `admin`

You will be **forced to change your password immediately** before you can access anything else.

### Changing Your Password
1. Click the **gear icon (⚙)** in the top-right corner.
2. Click **My Profile**.
3. In the right-hand panel, fill in your current password and new password.
4. Click **Change Password**.

> If you forget your password, contact the system administrator to reset it.

---

## 2. User Roles

| Role | What They Can Do |
|---|---|
| **Employee** | Apply for leave, view own requests and balance |
| **Line Manager** | Everything an employee can + approve/reject leave for their team |
| **HR Admin** | Everything a manager can + second-level approval + view all leaves + leave tracker |
| **Administration Director** | Everything HR can + final approval of all leave requests |
| **System Admin (superuser)** | Full access to all settings, user management, and system controls |

---

## 3. Employee Guide

### Viewing Your Dashboard
Your dashboard shows:
- **Deductible Leave Balance** — Your annual entitlement (18 days), how many you've used, and how many remain.
- **Non-Deductible Leaves Taken** — Days taken on leave types that do not affect your balance (e.g. Sick Leave, Maternity).
- **Pending Requests** — Requests awaiting approval.
- **Recent Leave Requests** — Your 5 most recent requests.

### Applying for Leave
1. Click **Apply for Leave** in the sidebar, or the **New Request** button.
2. Select a **Leave Type** from the dropdown.
   - A yellow badge means **Deductible** (subtracts from your balance).
   - A green badge means **Non-Deductible** (no balance impact).
3. Choose your **Start Date** and **End Date**.
   - The system automatically calculates working days (Monday–Saturday; Sundays are excluded).
4. Enter your **Reason**.
5. Attach a supporting document if required (e.g. for Sick Leave or Maternity Leave).
6. Click **Submit Request**.

### Viewing Your Requests
Click **My Requests** in the sidebar. You will see:
- All your leave requests with their current status.
- Your deductible balance summary and non-deductible breakdown.

### Request Statuses
| Status | Meaning |
|---|---|
| Pending Manager Approval | Waiting for your line manager |
| Pending HR Approval | Manager approved, waiting for HR |
| Pending Director Approval | HR approved, waiting for Director |
| Approved | Fully approved |
| Rejected | Denied at some stage |
| Cancelled | Cancelled by you or admin |

### Cancelling a Request
- Only requests that are still **Pending** (not yet approved or rejected) can be cancelled.
- On the request row in **My Requests**, click the red **X** button.
- Or open the request detail and click **Cancel Request**.

### Printing an Approval Letter
- Once your leave is **Approved**, a **Print** button appears on your request.
- Click it to open a printable approval letter.

---

## 4. Line Manager Guide

### Viewing Pending Approvals
Click **Manager Queue** in the sidebar. You will see all pending leave requests from your direct subordinates.

### Approving or Rejecting a Request
1. Click **Review** on a request.
2. Review the employee details, leave dates, reason, and their current balance.
3. Select **Approve** or **Reject**.
4. Optionally add **Remarks** (shown to HR and the employee).
5. Click **Submit Decision**.

- **Approve** → Request moves to HR for the second review.
- **Reject** → Request is closed. The employee's balance is not affected.

> **Note:** You can only action requests from employees assigned to you as supervisor. If a request is no longer pending (e.g. it was already cancelled), you will see a clear message instead of an error.

---

## 5. HR Admin Guide

### HR Approvals Queue
Click **HR Approvals** in the sidebar. This shows all requests that have been approved by the line manager and are now awaiting your review.

### Approving or Rejecting
Same as manager review — select Approve or Reject, add remarks, and submit.
- **Approve** → Request moves to the Administration Director for final sign-off.
- **Reject** → Request is closed.

### Viewing All Leave Requests
Click **All Requests** in the sidebar to see every leave request in the system. You can filter by:
- **Status** (pending, approved, rejected, cancelled)
- **Department**
- **Year**

### Leave Tracker
Click **Leave Tracker** to see a calendar/table view of who is currently on leave or has upcoming approved leave.
- Click any employee's name to see their full leave breakdown (deductible balance + non-deductible totals by type).

---

## 6. Administration Director Guide

### Director Queue
Click **Director Queue** in the sidebar. This shows all requests approved by both manager and HR, awaiting your final approval.

### Final Approval or Rejection
Same process as other approval stages.
- **Approve** → Leave is **Fully Approved**. The employee can print an approval letter.
- **Reject** → Request is closed.

### Dashboard
Your dashboard shows:
- Total employees, pending director approvals, approvals this year.
- Who is currently on leave.
- Monthly approved leave chart.

---

## 7. System Admin Guide

> All admin-only features are in the **Admin** section of the sidebar.

### Managing Employees
Go to **Employees** in the sidebar to:
- View all employees.
- Add a new employee (creates a user account automatically).
- Edit employee details (role, department, supervisor, position, phone).
- Reset any user's username or password (key icon button on each row).
- Deactivate an employee.

### Managing Departments
Go to **Departments** to add, view, or delete departments.

### Managing Leave Types
Go to **Leave Types** to:
- View all leave types with their deductible/non-deductible status.
- **Add** a new leave type — set name, deductibility, badge colour, document requirement, and active status.
- **Edit** any existing leave type.
- **Delete** a leave type (only if no leave requests reference it).
- **Restore Defaults** — re-adds any of the 9 standard leave types that are missing, without changing existing ones.

### System Settings
Go to **System Settings** (gear icon or sidebar) to access:

#### Reset Leave Balances (Bulk)
Resets all active employees' annual entitlement back to 18 days for the selected year. Leave request history is kept.

#### Per-Employee Balance Reset / Adjust
In the balance table, each employee row has:
- **Reset** — resets that employee to 18 days for the selected year.
- **Adjust** — opens a modal to set a custom entitlement (e.g. 15 or 21 days).

#### Export / Backup
Downloads a complete JSON backup of the entire system (employees, departments, leave types, balances, requests).

#### Import / Restore
Upload a previously exported JSON backup to restore data. Existing records with matching IDs are overwritten.

#### Soft Reset — Clear Leave Data
**Keeps:** All user accounts, employee profiles, departments, and leave types.
**Deletes:** All leave requests and all leave balances.
Confirmation phrase required: `RESET LEAVE DATA`

#### Full Factory Reset
**Keeps:** Nothing except the admin account.
**Deletes:** All employees, departments, leave data, and all non-admin users.
Admin username and password are reset to `admin` / `admin`. You are forced to change the password on next login.
Confirmation phrase required: `RESET EVERYTHING`

### Admin Override on Leave Requests
When viewing any leave request as admin, you see two extra panels on the right:

**Admin Override** (red panel):
- **Revert to Pending** — sends the request back to the beginning of the approval chain.
- **Cancel Leave** — cancels an approved leave. If it was deductible, the balance is automatically restored.

**Admin Corrections** (purple panel):
- Correct the **actual days taken** (e.g. if an 8-day leave was approved but employee only took 3 days, set it to 3 — balance and reports update instantly).
- Change the **status** directly.
- Add a **correction note** for the audit trail.

---

## 8. Leave Types Reference

| Leave Type | Deductible | Document Required |
|---|---|---|
| Annual Leave | Yes | No |
| Permission | Yes | No |
| Permission for School Leave | Yes | Yes |
| Sick Leave | No | Yes |
| Maternity Leave | No | Yes |
| Paternity Leave | No | Yes |
| Marriage Leave | No | No |
| Compassionate Leave | No | No |
| Study Leave | No | No |

**Deductible** = days are subtracted from the employee's 18-day annual entitlement.
**Non-Deductible** = days are tracked separately and do NOT affect the annual balance.

---

## 9. Working Days Policy

- Working days are **Monday through Saturday**.
- **Sundays are excluded** from all leave day calculations.
- The system automatically counts working days between the start and end date when a request is submitted.

---

*LeaveDesk — Magrabi ICO Cameroon Eye Institute*
