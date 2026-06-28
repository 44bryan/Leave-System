import re
import threading
import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.urls import reverse
from django.utils import timezone
from django.http import Http404

from accounts.models import Department, Employee
from notifications.utils import notify
from .models import (
    JobPosting, FormFieldConfig, ScoringCriterion,
    Application, ApplicationAnswer,
    FIELD_TYPE_TEXT, FIELD_TYPE_CHOICES, APPLICATION_STATUS_CHOICES,
)


# ─── Applicant email helper ────────────────────────────────────────────────────

_STATUS_EMAIL_TEMPLATES = {
    'under_review': (
        'Your Application is Under Review — {title}',
        'Thank you for applying for the {title} position at Africa Eye Foundation.\n\n'
        'We are pleased to inform you that your application is currently under review by our HR team. '
        'We will be in touch with further updates.\n\nBest regards,\nAEF HR Team',
    ),
    'shortlisted': (
        "You've Been Shortlisted — {title}",
        'Congratulations! We are pleased to inform you that your application for the {title} position '
        'has been shortlisted.\n\nWe will contact you shortly with the next steps in our selection process.'
        '\n\nBest regards,\nAEF HR Team',
    ),
    'interview': (
        'Interview Invitation — {title}',
        'Congratulations! You have been selected for an interview for the {title} position at Africa Eye Foundation.\n\n'
        'Our HR team will contact you directly with the interview schedule and details.\n\nBest regards,\nAEF HR Team',
    ),
    'hired': (
        'Congratulations — You Have Been Selected! — {title}',
        'Dear Applicant,\n\nWe are delighted to inform you that you have been selected for the {title} position '
        'at Africa Eye Foundation.\n\nOur HR team will be reaching out to you shortly with further details '
        'regarding your offer and onboarding.\n\nWelcome to the AEF family!\n\nBest regards,\nAEF HR Team',
    ),
    'rejected': (
        'Application Update — {title}',
        'Thank you for your interest in the {title} position at Africa Eye Foundation and for the time '
        'you invested in your application.\n\nAfter careful consideration, we regret to inform you that '
        'we will not be moving forward with your application at this time. We encourage you to apply for '
        'future openings that match your qualifications.\n\nWe wish you all the best in your career journey.'
        '\n\nBest regards,\nAEF HR Team',
    ),
}


def _email_applicant(applicant_name, applicant_email, status, posting_title):
    """Send a status-update email to an applicant in a background thread."""
    if not getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', False):
        return
    if not applicant_email:
        return
    tpl = _STATUS_EMAIL_TEMPLATES.get(status)
    if not tpl:
        return
    subject = tpl[0].format(title=posting_title)
    body = f'Dear {applicant_name},\n\n' + tpl[1].format(title=posting_title)
    try:
        send_mail(
            subject=f'[AEF HRM] {subject}',
            message=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'AEF HRM <noreply@aef-hrm.com>'),
            recipient_list=[applicant_email],
            fail_silently=True,
        )
    except Exception:
        pass


# ─── Permission helpers ───────────────────────────────────────────────────────

def _is_hr_or_admin(user):
    if user.is_superuser:
        return True
    try:
        emp = user.employee
        return emp.is_hr() or emp.is_director() or emp.is_ceo()
    except Exception:
        return False


# ─── Public views (no login required) ─────────────────────────────────────────

def job_board(request):
    """Public job board: list all open postings."""
    postings = list(JobPosting.objects.filter(status=JobPosting.STATUS_OPEN).select_related('department'))
    dept_counts = {}
    for p in postings:
        key = str(p.department) if p.department else 'General'
        dept_counts[key] = dept_counts.get(key, 0) + 1
    departments = [{'name': k, 'count': v} for k, v in sorted(dept_counts.items())]
    return render(request, 'recruitment/job_board.html', {
        'postings': postings,
        'departments': departments,
    })


def job_detail(request, pk):
    """Public: view job description."""
    posting = get_object_or_404(JobPosting, pk=pk, status=JobPosting.STATUS_OPEN)
    return render(request, 'recruitment/job_detail.html', {'posting': posting})


def apply(request, pk):
    """Public: submit an application for a job posting."""
    posting = get_object_or_404(JobPosting, pk=pk, status=JobPosting.STATUS_OPEN)
    fields = posting.form_fields.filter(is_enabled=True).order_by('field_order', 'pk')

    if request.method == 'POST':
        name  = request.POST.get('applicant_name', '').strip()
        email = request.POST.get('applicant_email', '').strip()
        cv    = request.FILES.get('cv_file')

        import os as _os
        _ALLOWED_CV_EXTS = {'.pdf', '.doc', '.docx'}
        _MAX_CV_BYTES = 10 * 1024 * 1024  # 10 MB

        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError as _VE
        errors = []
        if not name:
            errors.append('Full name is required.')
        if not email:
            errors.append('Email address is required.')
        else:
            try:
                validate_email(email)
            except _VE:
                errors.append('Please enter a valid email address.')
        if not cv:
            errors.append('Please upload your CV / résumé.')
        else:
            ext = _os.path.splitext(cv.name)[1].lower()
            if ext not in _ALLOWED_CV_EXTS:
                errors.append('CV must be a PDF, DOC, or DOCX file.')
            elif cv.size > _MAX_CV_BYTES:
                errors.append('CV file size must not exceed 10 MB.')

        # Validate enabled required fields
        for field in fields:
            if field.is_required:
                if field.field_type == 'file':
                    val = request.FILES.get(field.field_name)
                else:
                    val = request.POST.get(field.field_name, '').strip()
                if not val:
                    errors.append(f'{field.label} is required.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'recruitment/apply.html', {
                'posting':         posting,
                'fields':          fields,
                'applicant_name':  name,
                'applicant_email': email,
            })

        with transaction.atomic():
            app = Application.objects.create(
                posting=posting,
                applicant_name=name,
                applicant_email=email,
                cv_file=cv,
            )
            # Save answers for all enabled fields
            answers_to_create = []
            for field in fields:
                if field.field_type == 'file':
                    uploaded_file = request.FILES.get(field.field_name)
                    val = uploaded_file.name if uploaded_file else ''
                else:
                    val = request.POST.get(field.field_name, '').strip()
                answers_to_create.append(ApplicationAnswer(
                    application=app,
                    field_name=field.field_name,
                    value=val,
                ))
            ApplicationAnswer.objects.bulk_create(answers_to_create)
            # Auto-score
            app.compute_score()

        # Notify all HR users of the new application
        detail_url = reverse('recruitment:applicant_detail', kwargs={'posting_pk': posting.pk, 'pk': app.pk})
        for hr_emp in Employee.objects.filter(role='hr', is_active=True).select_related('user'):
            notify(
                hr_emp.user,
                f'New Application — {posting.title}',
                f'{name} has submitted an application for the {posting.title} position.\n\n'
                f'Score: {int(app.score)} pts  |  Email: {email}',
                notification_type='system',
                url=detail_url,
            )

        return redirect('recruitment:apply_success', pk=posting.pk)

    return render(request, 'recruitment/apply.html', {
        'posting':         posting,
        'fields':          fields,
        'applicant_name':  '',
        'applicant_email': '',
    })


def apply_success(request, pk):
    posting = get_object_or_404(JobPosting, pk=pk)
    return render(request, 'recruitment/apply_success.html', {'posting': posting})


# ─── HR views (login required) ────────────────────────────────────────────────

@login_required
def posting_list(request):
    if not _is_hr_or_admin(request.user):
        messages.error(request, 'Only HR and above can access recruitment management.')
        return redirect('dashboard:home')

    postings = JobPosting.objects.select_related('department', 'created_by').all()
    status_filter = request.GET.get('status', '')
    if status_filter:
        postings = postings.filter(status=status_filter)

    return render(request, 'recruitment/posting_list.html', {
        'postings':      postings,
        'status_filter': status_filter,
        'STATUS_CHOICES': JobPosting.STATUS_CHOICES,
    })


@login_required
def posting_create(request):
    if not _is_hr_or_admin(request.user):
        messages.error(request, 'Only HR and above can create job postings.')
        return redirect('recruitment:list')

    departments = Department.objects.all()

    if request.method == 'POST':
        title  = request.POST.get('title', '').strip()
        desc   = request.POST.get('description', '').strip()
        if not title or not desc:
            messages.error(request, 'Title and description are required.')
            return render(request, 'recruitment/posting_form.html', {
                'departments': departments,
                'type_choices': JobPosting.TYPE_CHOICES,
                'post': request.POST,
            })
        dept_pk = request.POST.get('department')
        dept = Department.objects.filter(pk=dept_pk).first() if dept_pk else None

        dl_str = request.POST.get('deadline', '').strip()
        deadline = None
        if dl_str:
            from datetime import date
            try:
                deadline = date.fromisoformat(dl_str)
            except ValueError:
                pass

        posting = JobPosting.objects.create(
            title=title,
            department=dept,
            location=request.POST.get('location', '').strip(),
            employment_type=request.POST.get('employment_type', JobPosting.TYPE_FULL_TIME),
            description=desc,
            requirements=request.POST.get('requirements', '').strip(),
            status=request.POST.get('status', JobPosting.STATUS_DRAFT),
            deadline=deadline,
            created_by=request.user,
        )
        posting.create_default_fields()
        messages.success(request, f'Job posting "{posting.title}" created. Configure the application form below.')
        return redirect('recruitment:form_config', pk=posting.pk)

    return render(request, 'recruitment/posting_form.html', {
        'departments':  departments,
        'type_choices': JobPosting.TYPE_CHOICES,
        'post': {},
    })


@login_required
def posting_edit(request, pk):
    if not _is_hr_or_admin(request.user):
        messages.error(request, 'Only HR and above can edit job postings.')
        return redirect('recruitment:list')

    posting = get_object_or_404(JobPosting, pk=pk)
    departments = Department.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        desc  = request.POST.get('description', '').strip()
        if not title or not desc:
            messages.error(request, 'Title and description are required.')
        else:
            dept_pk = request.POST.get('department')
            dept = Department.objects.filter(pk=dept_pk).first() if dept_pk else None
            dl_str = request.POST.get('deadline', '').strip()
            deadline = None
            if dl_str:
                from datetime import date
                try:
                    deadline = date.fromisoformat(dl_str)
                except ValueError:
                    pass
            posting.title           = title
            posting.department      = dept
            posting.location        = request.POST.get('location', '').strip()
            posting.employment_type = request.POST.get('employment_type', JobPosting.TYPE_FULL_TIME)
            posting.description     = desc
            posting.requirements    = request.POST.get('requirements', '').strip()
            posting.status          = request.POST.get('status', posting.status)
            posting.deadline        = deadline
            posting.save()
            messages.success(request, 'Job posting updated.')
            return redirect('recruitment:list')

    return render(request, 'recruitment/posting_form.html', {
        'posting':      posting,
        'departments':  departments,
        'type_choices': JobPosting.TYPE_CHOICES,
        'post': posting,
    })


@login_required
def posting_delete(request, pk):
    if not _is_hr_or_admin(request.user):
        messages.error(request, 'Only HR and above can delete job postings.')
        return redirect('recruitment:list')
    posting = get_object_or_404(JobPosting, pk=pk)
    if request.method == 'POST':
        title = posting.title
        posting.delete()
        messages.success(request, f'Job posting "{title}" deleted.')
    return redirect('recruitment:list')


@login_required
def form_config(request, pk):
    """Configure which fields appear on the application form for this posting."""
    if not _is_hr_or_admin(request.user):
        messages.error(request, 'Only HR and above can configure application forms.')
        return redirect('recruitment:list')

    posting = get_object_or_404(JobPosting, pk=pk)
    # Ensure defaults exist
    posting.create_default_fields()

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'save_fields':
            valid_types = [c[0] for c in FIELD_TYPE_CHOICES]
            fields = posting.form_fields.all()
            for field in fields:
                enabled   = f'enabled_{field.pk}' in request.POST
                required  = f'required_{field.pk}' in request.POST
                label     = request.POST.get(f'label_{field.pk}', field.label).strip() or field.label
                order     = request.POST.get(f'order_{field.pk}', str(field.field_order))
                ph        = request.POST.get(f'placeholder_{field.pk}', '').strip()
                options   = request.POST.get(f'options_{field.pk}', field.options).strip()
                new_type  = request.POST.get(f'type_{field.pk}', field.field_type)
                try:
                    order = int(order)
                except ValueError:
                    order = field.field_order
                field.is_enabled   = enabled
                field.is_required  = required and enabled
                field.label        = label
                field.field_order  = order
                field.placeholder  = ph
                field.options      = options
                if new_type in valid_types:
                    field.field_type = new_type
                field.save(update_fields=['is_enabled', 'is_required', 'label', 'field_order', 'placeholder', 'options', 'field_type'])
            messages.success(request, 'Form configuration saved.')
            return redirect('recruitment:form_config', pk=pk)

        if action == 'add_custom':
            label      = request.POST.get('new_label', '').strip()
            field_type = request.POST.get('new_field_type', FIELD_TYPE_TEXT)
            required   = 'new_required' in request.POST
            options    = request.POST.get('new_options', '').strip()
            ph         = request.POST.get('new_placeholder', '').strip()
            if not label:
                messages.error(request, 'A label is required for the custom field.')
            else:
                # Generate a safe field_name from label
                field_name = re.sub(r'[^a-z0-9_]', '_', label.lower())[:60]
                field_name = f'custom_{field_name}'
                # Ensure uniqueness within this posting
                base = field_name
                i = 2
                while posting.form_fields.filter(field_name=field_name).exists():
                    field_name = f'{base}_{i}'
                    i += 1
                max_order = posting.form_fields.aggregate(m=Max('field_order'))['m'] or 0
                FormFieldConfig.objects.create(
                    posting=posting,
                    field_name=field_name,
                    label=label,
                    field_type=field_type,
                    is_enabled=True,
                    is_required=required,
                    field_order=max_order + 1,
                    options=options,
                    placeholder=ph,
                    is_custom=True,
                )
                messages.success(request, f'Custom field "{label}" added.')
            return redirect('recruitment:form_config', pk=pk)

        if action == 'delete_field':
            field_pk = request.POST.get('field_pk')
            field = posting.form_fields.filter(pk=field_pk).first()
            if field:
                field.delete()
                messages.success(request, 'Custom field deleted.')
            return redirect('recruitment:form_config', pk=pk)

    fields = posting.form_fields.all()
    return render(request, 'recruitment/form_config.html', {
        'posting':        posting,
        'fields':         fields,
        'FIELD_TYPE_CHOICES': FIELD_TYPE_CHOICES,
    })


@login_required
def scoring_config(request, pk):
    """Configure auto-scoring criteria for a posting."""
    if not _is_hr_or_admin(request.user):
        messages.error(request, 'Only HR and above can configure scoring criteria.')
        return redirect('recruitment:list')

    posting = get_object_or_404(JobPosting, pk=pk)
    fields  = posting.form_fields.filter(is_enabled=True).order_by('field_order')

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'add_criterion':
            field_name = request.POST.get('field_name', '').strip()
            label      = request.POST.get('label', '').strip()
            condition  = request.POST.get('condition', '')
            value      = request.POST.get('value', '').strip()
            points_str = request.POST.get('points', '0')
            try:
                points = int(points_str)
            except ValueError:
                points = 0
            if not field_name or not label or not condition:
                messages.error(request, 'Field, label, and condition are required.')
            else:
                ScoringCriterion.objects.create(
                    posting=posting,
                    field_name=field_name,
                    label=label,
                    condition=condition,
                    value=value,
                    points=points,
                )
                messages.success(request, f'Scoring rule "{label}" added.')
            return redirect('recruitment:scoring_config', pk=pk)

        if action == 'delete_criterion':
            crit_pk = request.POST.get('criterion_pk')
            ScoringCriterion.objects.filter(pk=crit_pk, posting=posting).delete()
            messages.success(request, 'Scoring rule deleted.')
            return redirect('recruitment:scoring_config', pk=pk)

        if action == 'rescore_all':
            count = 0
            for app in posting.applications.prefetch_related('answers'):
                app.compute_score()
                count += 1
            messages.success(request, f'Re-scored {count} application(s).')
            return redirect('recruitment:scoring_config', pk=pk)

    criteria = posting.scoring_criteria.all()
    return render(request, 'recruitment/scoring_config.html', {
        'posting':   posting,
        'criteria':  criteria,
        'fields':    fields,
        'COND_CHOICES': ScoringCriterion.COND_CHOICES,
    })


@login_required
def applicant_list(request, pk):
    """HR: ranked list of applicants for a posting."""
    if not _is_hr_or_admin(request.user):
        return redirect('recruitment:list')

    posting = get_object_or_404(JobPosting, pk=pk)
    apps    = posting.applications.all()

    status_filter = request.GET.get('status', '')
    if status_filter:
        apps = apps.filter(status=status_filter)

    return render(request, 'recruitment/applicant_list.html', {
        'posting':        posting,
        'applications':   apps,
        'status_filter':  status_filter,
        'STATUS_CHOICES': APPLICATION_STATUS_CHOICES,
    })


@login_required
def applicant_detail(request, posting_pk, pk):
    """HR: full applicant profile."""
    if not _is_hr_or_admin(request.user):
        return redirect('recruitment:list')

    posting = get_object_or_404(JobPosting, pk=posting_pk)
    app        = get_object_or_404(Application, pk=pk, posting=posting)
    answer_map = {a.field_name: a.value for a in app.answers.all()}
    fields     = posting.form_fields.filter(is_enabled=True).order_by('field_order')
    field_answers = [(f, answer_map.get(f.field_name, '')) for f in fields]

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'update_status':
            new_status = request.POST.get('status', app.status)
            valid = [s[0] for s in APPLICATION_STATUS_CHOICES]
            if new_status in valid:
                app.status = new_status
                app.reviewed_by = request.user
                if new_status == 'rejected':
                    app.rejection_reason = request.POST.get('rejection_reason', '').strip()
                if new_status == 'interview':
                    dt_str = request.POST.get('interview_date', '').strip()
                    if dt_str:
                        from datetime import datetime
                        try:
                            app.interview_date = datetime.fromisoformat(dt_str)
                        except ValueError:
                            pass
                app.save()
                # Email the applicant about their status change (background thread)
                threading.Thread(
                    target=_email_applicant,
                    args=(app.applicant_name, app.applicant_email, new_status, posting.title),
                    daemon=True,
                ).start()
                messages.success(request, f'Status updated to {app.get_status_display()}.')
            return redirect('recruitment:applicant_detail', posting_pk=posting_pk, pk=pk)

        if action == 'save_notes':
            app.hr_notes = request.POST.get('hr_notes', '').strip()
            app.interview_notes = request.POST.get('interview_notes', '').strip()
            app.save(update_fields=['hr_notes', 'interview_notes'])
            messages.success(request, 'Notes saved.')
            return redirect('recruitment:applicant_detail', posting_pk=posting_pk, pk=pk)

    return render(request, 'recruitment/applicant_detail.html', {
        'posting':       posting,
        'app':           app,
        'field_answers': field_answers,
        'STATUS_CHOICES': APPLICATION_STATUS_CHOICES,
    })
