from django.shortcuts import redirect
from django.contrib import messages


def csrf_failure(request, reason=''):
    """
    Replace Django's default 403 CSRF page with a graceful redirect.
    The user is sent back to the page they came from (or home) with a
    friendly 'please try again' notice instead of a scary error page.
    """
    referer = request.META.get('HTTP_REFERER', '')
    messages.warning(
        request,
        'Your session token expired. Please try again — your form has been reloaded.'
    )
    if referer:
        return redirect(referer)
    return redirect('dashboard:home')
