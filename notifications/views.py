from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notification


@login_required
def notification_list(request):
    notifications = request.user.system_notifications.all()
    # Mark all as read when the page is opened
    request.user.system_notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications,
    })


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
