# 👁 MICEI HRM — Eye Hospital HR Leave Management System

A fully-featured, web-based leave management system built with Django + Bootstrap 5 for the HR Department.

---

## 🚀 Quick Setup (Windows)

### Step 1 — Install Python
Download Python 3.11+ from https://python.org and install it. Make sure to tick **"Add Python to PATH"**.

### Step 2 — Extract and Open Folder
Extract the ZIP, then open a terminal (Command Prompt or PowerShell) inside the `leave_system` folder.

### Step 3 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Set Up Database
```bash
python manage.py makemigrations accounts
python manage.py makemigrations leaves
python manage.py makemigrations dashboard
python manage.py migrate
```

### Step 5 — Load Demo Data
```bash
python manage.py seed_data
```

### Step 6 — Start the Server
```bash
python manage.py runserver
```

### Step 7 — Open in Browser
Go to: **http://127.0.0.1:8000**

---

## 🔐 Demo Login Credentials

| Role         | Username     | Password      |
|--------------|-------------|---------------|
| HR Admin     | `hr_admin`  | `hospital2024` |
| Line Manager | `dr_fon`    | `hospital2024` |
| Employee     | `nurse_mary`| `hospital2024` |

---

## 👥 User Roles

| Role | Capabilities |
|------|-------------|
| **Employee** | Submit leave requests, view own history, check balance |
| **Line Manager** | Everything an Employee can do + approve/reject team requests |
| **HR Admin** | Full access — final approvals, all records, employee management, dashboard |

---

## 🔄 Approval Workflow

```
Employee Submits Request
         ↓
   Status: PENDING
         ↓
  Line Manager Reviews
     ↙         ↘
Approve        Reject
   ↓              ↓
MANAGER        REJECTED
APPROVED       (Final)
   ↓
 HR Reviews
  ↙        ↘
Approve    Reject
   ↓          ↓
APPROVED   REJECTED
(Final)    (Final)
```

> ⚠️ HR cannot approve a request unless the Line Manager has already approved it first.

---

## 📋 Leave Types

- Annual Leave (18 days/year per employee)
- Sick Leave
- Marriage Leave
- Maternity / Paternity Leave
- Compassionate Leave
- Study Leave

---

## 📊 Features

- ✅ Multi-level approval workflow (Manager → HR)
- ✅ Real-time leave balance tracking (18 days/year)
- ✅ HR Analytics Dashboard with charts
- ✅ Department-level leave breakdown
- ✅ Who's on leave today (live view)
- ✅ Low balance alerts
- ✅ Document upload support
- ✅ Role-based access control
- ✅ Leave request cancellation
- ✅ Full audit trail (who approved, when, remarks)
- ✅ Responsive design (works on mobile)

---

## 🛠 Adding Real Employees (HR Admin)

1. Log in as `hr_admin`
2. Go to **Employees → Add New Employee**
3. Fill in their details and assign a supervisor
4. Their leave balance (18 days) is created automatically

---

## 🔧 Production Deployment

When ready to host online:
1. Change `SECRET_KEY` in `settings.py`
2. Set `DEBUG = False`
3. Configure `ALLOWED_HOSTS` with your domain
4. Switch to PostgreSQL database
5. Use gunicorn + nginx

---

*Built for Eye Hospital HR Department · Local deployment ready*
