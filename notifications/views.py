from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from .models import Notification


@login_required
def notification_list(request):
    notifications = request.user.system_notifications.all()
    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications,
    })


@login_required
def notification_detail(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notif.is_read:
        notif.is_read = True
        notif.save(update_fields=['is_read'])
    # Fix legacy URL if needed
    if notif.url:
        fixed = _fix_legacy_url(notif.url)
        if fixed != notif.url:
            notif.url = fixed
            notif.save(update_fields=['url'])
    return render(request, 'notifications/notification_detail.html', {'notif': notif})


def _fix_legacy_url(url):
    """Rewrite legacy notification URLs that used the old /leaves/<pk>/action/<role>/ format."""
    import re
    # Old format: /leaves/<pk>/action/manager/ → /leaves/manager/action/<pk>/
    m = re.match(r'^/leaves/(\d+)/action/(manager|hr|director)/$', url)
    if m:
        pk, role = m.group(1), m.group(2)
        return f'/leaves/{role}/action/{pk}/'
    # Old contract issued URL
    if url == '/contracts/my-contract/':
        return '/contracts/my/'
    return url


@login_required
def mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    url = notif.url or ''
    # Rewrite any legacy-format URLs stored in the DB
    if url:
        url = _fix_legacy_url(url)
        if url != notif.url:
            notif.url = url  # persist the corrected URL so it doesn't need fixing again
    notif.save()
    if url:
        # Validate the URL resolves before redirecting — fall back to notification list on 404
        try:
            from django.urls import resolve
            resolve(url)
            return redirect(url)
        except Exception:
            pass
    return redirect('notifications:list')


@login_required
def mark_all_read(request):
    if request.method == 'POST':
        request.user.system_notifications.filter(is_read=False).update(is_read=True)
    return redirect('notifications:list')


@login_required
def unread_count(request):
    count = request.user.system_notifications.filter(is_read=False).count()
    return JsonResponse({'count': count})


@login_required
def test_email(request):
    """Superuser-only: send a test email and show the result on screen."""
    if not request.user.is_superuser:
        return HttpResponse('Forbidden', status=403)

    from django.conf import settings
    from django.core.mail import EmailMultiAlternatives

    lines = []
    lines.append(f"EMAIL_NOTIFICATIONS_ENABLED : {getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', '(not set)')}")
    lines.append(f"EMAIL_BACKEND               : {getattr(settings, 'EMAIL_BACKEND', '(not set)')}")
    lines.append(f"EMAIL_HOST                  : {getattr(settings, 'EMAIL_HOST', '(not set)')}")
    lines.append(f"EMAIL_PORT                  : {getattr(settings, 'EMAIL_PORT', '(not set)')}")
    lines.append(f"EMAIL_USE_TLS               : {getattr(settings, 'EMAIL_USE_TLS', '(not set)')}")
    lines.append(f"EMAIL_HOST_USER             : {getattr(settings, 'EMAIL_HOST_USER', '(not set)')}")
    lines.append(f"EMAIL_HOST_PASSWORD         : {'*** (set)' if getattr(settings, 'EMAIL_HOST_PASSWORD', '') else '(EMPTY!)'}")
    lines.append(f"DEFAULT_FROM_EMAIL          : {getattr(settings, 'DEFAULT_FROM_EMAIL', '(not set)')}")
    lines.append(f"Your email (logged-in user) : {request.user.email or '(EMPTY!)'}")
    lines.append("")

    if not request.user.email:
        lines.append("ERROR: Your user account has no email address — cannot send test.")
    else:
        try:
            msg = EmailMultiAlternatives(
                subject='[LeaveDesk] Test Email',
                body='This is a test email from LeaveDesk HR System.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[request.user.email],
            )
            msg.send()
            lines.append(f"SUCCESS: email sent to {request.user.email}")
        except Exception as e:
            lines.append(f"FAILED: {e}")

    return HttpResponse("<pre style='font-family:monospace;padding:24px'>" + "\n".join(lines) + "</pre>")
