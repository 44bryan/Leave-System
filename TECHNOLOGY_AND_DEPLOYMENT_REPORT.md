# MICEI HRM — Technology & Deployment Report
## Prepared for Administration — Budget & Infrastructure Planning
**Institution:** Magrabi ICO Cameroon Eye Institution (MICEI)
**System:** MICEI Human Resource Management System (HRM)
**Prepared:** March 2026

---

## 1. WHAT THE SYSTEM DOES

MICEI HRM is a complete web-based Human Resource Management platform built specifically for MICEI. It replaces paper-based HR processes with a secure, digital, role-based system accessible from any device (phone, tablet, computer) with internet access.

### Core Modules

| Module | What It Does |
|--------|-------------|
| **Leave Management** | Staff submit leave requests digitally. Requests flow through a 4-step approval chain: Unit Head → Line Manager → HR → Finance Director. Balances are tracked automatically. |
| **Digital Signatures** | Approvers sign leave forms digitally using a touch/mouse draw pad. Signatures are embedded in official PDF leave authorization forms. |
| **PDF Leave Authorization** | The system generates official, professionally formatted bilingual (English/French) PDF leave authorization forms, ready to print or archive. |
| **Contract Management** | HR manages staff contracts: CDI (Permanent), CDD (Fixed Term), WACS Residency, and Internships. The system tracks expiry dates and alerts HR when contracts are nearing renewal. |
| **Discipline Records** | HR and managers issue and track discipline notices (verbal warnings, written cautions, final warnings, suspensions, dismissals) with a multi-level review workflow. |
| **Employee Profiles** | Full employee records including personal data, qualifications, department transfers history, document uploads (ID, diplomas, certificates), digital signatures. |
| **Role-Based Dashboards** | Each role (Employee, Unit Head, Manager, HR, Director, CEO, Admin) sees a customized dashboard with relevant statistics and pending actions. |
| **Email Notifications** | Automatic email alerts sent to staff and approvers at each step of the leave and contract workflow. |
| **Excel & PDF Reports** | HR and management can download filtered reports of leaves, contracts, and discipline records as Excel files or PDF summaries. |
| **Retirement Tracker** | Flags employees within 3 years of retirement age (60 years). |
| **Birthday Calendar** | Monthly birthday overview for all staff. |
| **French/English Bilingual** | Full interface and official forms available in both English and French. |

---

## 2. TECHNOLOGY STACK

### Core Platform

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Programming Language** | Python | 3.11 | Application logic |
| **Web Framework** | Django | 5.0.6 | Core web application structure, authentication, database management |
| **Web Server** | Gunicorn | 21.2.0 | Production-grade server that handles HTTP requests |
| **Frontend Framework** | Bootstrap | 5.3 | Responsive UI — works on phone, tablet, and desktop |
| **Icons** | Bootstrap Icons | Built-in | UI icons throughout the interface |
| **Charts** | Chart.js | CDN | Dashboard graphs and statistics |
| **Fonts** | Plus Jakarta Sans | Google Fonts | Interface typography |

### Database

| Environment | Database | Notes |
|-------------|----------|-------|
| **Production (live)** | PostgreSQL | Hosted on Railway cloud. Reliable, persistent, industry standard. |
| **Development (local)** | SQLite | Lightweight file-based database used for building and testing. |

### Email Service

| Component | Service | Provider | Purpose |
|-----------|---------|----------|---------|
| **Email Sending** | Resend | resend.com | Sends automated email notifications to staff when leave is submitted, approved, rejected, or when contracts change. |
| **Django Email Connector** | django-anymail | PyPI | Connects Django to Resend API |

### File Storage

| Component | Service | Purpose |
|-----------|---------|---------|
| **Uploaded Files** | Cloudinary | Stores all uploaded files (leave supporting documents, employee documents, signatures, ID copies, diplomas) securely in the cloud. Files survive server restarts and are accessible to all users. |
| **Static Files** | WhiteNoise | Serves the application's static assets (CSS, JavaScript, logo, images) efficiently from the web server itself. |

### PDF Generation

| Component | Library | Purpose |
|-----------|---------|---------|
| **Leave Authorization PDF** | ReportLab | Generates the official bilingual PDF leave authorization forms with embedded logo, digital signatures, and approval grid. |
| **Image Processing** | Pillow | Processes and composites digital signature images into PDF forms. |
| **PDF Utilities** | PyMuPDF | Additional PDF handling utilities. |

### Data Export

| Component | Library | Purpose |
|-----------|---------|---------|
| **Excel Reports** | openpyxl | Generates downloadable Excel (.xlsx) reports for leaves, contracts, and discipline records. |

### Deployment Platform

| Component | Service | Purpose |
|-----------|---------|---------|
| **Cloud Hosting** | Railway (railway.app) | Hosts and runs the application on the internet. Handles server infrastructure, automatic deployments from code changes. |
| **Code Repository** | GitHub (github.com) | Stores all application code. Every code change is saved here before being deployed to Railway. |

---

## 3. EXTERNAL SERVICES — CURRENT STATUS

| Service | Provider | Current Plan | Purpose | Status |
|---------|----------|-------------|---------|--------|
| **Cloud Hosting** | Railway | Hobby Plan (~$5/month) | Hosts the live application | ✅ Active |
| **Database** | Railway PostgreSQL | Included with hosting | Stores all HR data | ✅ Active |
| **Email Sending** | Resend | Free Tier (100 emails/day) | Email notifications to staff | ✅ Active |
| **File Storage** | Cloudinary | Free Tier (25GB) | Stores uploaded documents and signatures | ✅ Active |
| **Code Repository** | GitHub | Free | Source code version control | ✅ Active |

---

## 4. WHAT HAS BEEN BUILT (COMPLETED FEATURES)

### Authentication & User Management
- ✅ Secure login/logout with Django's built-in authentication
- ✅ 10 user roles: Employee, Unit Head, Line Manager, HR Admin, Administration Director, Finance Director, CEO, Intern, WACS Resident, System Administrator
- ✅ Employee profile management (create, edit, deactivate)
- ✅ Bulk employee import via Excel file
- ✅ Employee document vault (ID, diplomas, contracts, medical certificates)
- ✅ Department management and transfer tracking
- ✅ Digital signature capture (draw-pad on any touch screen)

### Leave Management
- ✅ Leave request submission with supporting document upload
- ✅ 4-step approval chain: Unit Head → Line Manager → HR → Finance Director
- ✅ Digital signatures collected at every approval step
- ✅ Professional bilingual PDF leave authorization (ready to print or archive)
- ✅ Automatic leave balance tracking (18 days/year standard)
- ✅ Carry-forward logic (unused days roll to next year)
- ✅ 9 leave types: Annual, Sick, Maternity, Paternity, Marriage, Compassionate, Permission, Study Leave, School Permission
- ✅ HR leave tracker (see all employee balances at a glance)
- ✅ Year-end balance reset tools

### Contract Management
- ✅ Issue contracts: CDI (Permanent), CDD (Fixed Term), Internship, WACS Residency
- ✅ 6 internship types: Academic, Professional, Pre-Employment, Vocational, Observation, Other
- ✅ Contract expiry alerts (60 days and 30 days warnings)
- ✅ Contract renewal and termination workflow
- ✅ Working department tracking for interns and residents
- ✅ Contract history chain (renewal links to previous contract)

### Discipline Management
- ✅ Issue discipline notices: Verbal Warning, Written Caution, Final Warning, Suspension, Dismissal
- ✅ Suspension dates auto-calculated (8 days standard)
- ✅ Multi-level sanction proposal: Manager → HR → Director
- ✅ Dismissal alert system (flags accounts for HR deactivation)
- ✅ Discipline statistics dashboard

### Reporting & Exports
- ✅ Excel export: Leave requests (filterable by year, department, employee)
- ✅ Excel export: Contracts (filterable by type, department, employee)
- ✅ Excel export: Discipline records (filterable by type, department)
- ✅ PDF leave authorization forms
- ✅ Retirement risk tracker (employees within 3 years of age 60)
- ✅ Birthday calendar (monthly view)

### Notifications
- ✅ In-app bell notifications (unread count badge)
- ✅ Email notifications via Resend with embedded logo
- ✅ Automatic alerts for: leave submission, each approval step, rejection, contract issuance/renewal/termination, discipline notices

### System Administration
- ✅ Admin dashboard with full control panel
- ✅ Factory reset options (full, soft, year-end)
- ✅ Leave balance adjustments per employee
- ✅ Leave type management (add, edit, deactivate)
- ✅ System data export/import (JSON)
- ✅ Bilingual interface (English and French)

---

## 5. DEPLOYMENT REQUIREMENTS

To keep the system running in production, the following services are required:

### Minimum Requirements (Current Free/Low-Cost Setup)

| Service | Provider | Cost | Limit | Upgrade When |
|---------|----------|------|-------|-------------|
| **App Hosting** | Railway | ~$5/month | 512MB RAM, shared CPU | Staff grows beyond 100 active users |
| **Database** | Railway PostgreSQL | ~$5/month | 1GB storage | Database exceeds 1GB |
| **Email** | Resend Free | Free | 100 emails/day | Daily emails exceed 100 |
| **File Storage** | Cloudinary Free | Free | 25GB storage | Uploaded files exceed 25GB |
| **Code Repository** | GitHub Free | Free | Unlimited public/private repos | Never (free is sufficient) |

**Estimated Monthly Cost at Current Scale: ~$10/month (USD)**

### Recommended Production Setup (For Larger Scale)

| Service | Provider | Cost | Limit |
|---------|----------|------|-------|
| **App Hosting** | Railway Pro | ~$20/month | 8GB RAM, dedicated resources |
| **Database** | Railway PostgreSQL Pro | ~$10/month | 10GB storage |
| **Email** | Resend Pro | ~$20/month | 50,000 emails/month |
| **File Storage** | Cloudinary Plus | ~$89/month | 225GB storage |
| **Domain Name** | Any registrar | ~$15/year | Custom domain (e.g. hrm.micei.cm) |

**Estimated Monthly Cost at Full Scale: ~$140/month (USD)**

### Internet Requirements (On-Site)
- **Minimum:** Stable internet connection (at least 5 Mbps) for staff to access the system
- The application is **cloud-hosted** — no server hardware needs to be purchased or maintained on-site
- Staff access the system through any modern web browser (Chrome, Firefox, Edge, Safari)

---

## 6. WHAT IS NOT NEEDED (Cost Savings)

Because this is a cloud-hosted web application, MICEI does **NOT** need to purchase:

| Item | Why Not Needed |
|------|---------------|
| Physical server hardware | Application runs on Railway cloud servers |
| Server room / rack equipment | No on-premises infrastructure required |
| Windows Server / SQL Server licenses | Uses open-source Django + PostgreSQL |
| Microsoft Office for reports | Excel exports work with any spreadsheet software (including free LibreOffice) |
| Dedicated IT maintenance contract | System maintains itself (automatic deployments, cloud backups) |
| Separate backup solution | PostgreSQL on Railway has automated backups |

---

## 7. OPEN SOURCE SOFTWARE USED (No License Cost)

All software libraries used in this project are open source and free to use commercially:

| Library | License | Cost |
|---------|---------|------|
| Python 3.11 | PSF License | Free |
| Django 5.0.6 | BSD License | Free |
| PostgreSQL | PostgreSQL License | Free |
| Bootstrap 5 | MIT License | Free |
| ReportLab | BSD License | Free |
| Chart.js | MIT License | Free |
| openpyxl | MIT License | Free |
| Pillow | HPND License | Free |
| WhiteNoise | MIT License | Free |
| All other Python packages | Various open-source | Free |

---

## 8. SECURITY & DATA PROTECTION

| Aspect | Implementation |
|--------|---------------|
| **Authentication** | Django's industry-standard authentication with hashed passwords |
| **Access Control** | Role-based permissions — each user only sees what their role allows |
| **Data Encryption** | All data transmitted over HTTPS (SSL/TLS encryption) via Railway |
| **Database** | PostgreSQL on Railway — isolated, not publicly accessible |
| **File Storage** | Cloudinary — encrypted at rest, served over HTTPS |
| **Session Security** | Django session framework with secure cookies |
| **Audit Trail** | Department transfer history, leave approval history, all actions logged with timestamps and user identity |

---

## 9. SYSTEM CAPACITY ESTIMATES

| Metric | Current Capacity | Notes |
|--------|-----------------|-------|
| **Concurrent Users** | ~50 | On current Railway Hobby plan |
| **Total Staff Records** | Unlimited | Database grows as needed |
| **Leave Requests / Year** | Unlimited | Historical data preserved indefinitely |
| **File Storage** | 25GB | Cloudinary free tier |
| **Email Notifications** | 100/day | Resend free tier |
| **Uptime** | ~99.5% | Railway cloud SLA |

---

## 10. SUMMARY FOR ADMINISTRATION

This system was built entirely using open-source software at minimal cost. The only recurring costs are cloud hosting services, which replace the cost of physical server hardware and IT maintenance.

**What Was Built:**
A complete, custom HR management system tailored specifically to MICEI's workflow, roles, and bilingual (English/French) requirements. No commercial HR software was purchased — the system was built from scratch.

**What Is Running Right Now:**
The system is live on the internet, accessible from any device with a browser, and has been tested with real data.

**What Is Needed Going Forward:**
- Continue the current Railway + Cloudinary + Resend subscriptions (~$10/month)
- A custom domain name for a professional URL (~$15/year, optional)
- Stable internet at MICEI for staff to access the system

**Total Estimated Annual Cost to Operate:** ~$120–$135 USD/year at current scale.

---

*Document prepared by the MICEI HRM development team — March 2026*
*For technical questions, refer to PROJECT_DOCUMENT.md*
