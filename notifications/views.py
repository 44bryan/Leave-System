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


@login_required
def mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save()
    if notif.url:
        return redirect(notif.url)
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
