import re
from django.core.management.base import BaseCommand
from notifications.models import Notification


URL_FIXES = [
    # Old: /leaves/<pk>/action/manager/ → /leaves/manager/action/<pk>/
    (re.compile(r'^/leaves/(\d+)/action/(manager|hr|director)/$'),
     lambda m: f'/leaves/{m.group(2)}/action/{m.group(1)}/'),
    # Old: /contracts/my-contract/ → /contracts/my/
    (re.compile(r'^/contracts/my-contract/$'),
     lambda m: '/contracts/my/'),
]


class Command(BaseCommand):
    help = 'Rewrite legacy notification URLs to current URL patterns'

    def handle(self, *args, **options):
        fixed = 0
        for notif in Notification.objects.exclude(url=''):
            new_url = notif.url
            for pattern, replacer in URL_FIXES:
                m = pattern.match(new_url)
                if m:
                    new_url = replacer(m)
                    break
            if new_url != notif.url:
                self.stdout.write(f'  Fix #{notif.pk}: {notif.url!r} → {new_url!r}')
                notif.url = new_url
                notif.save(update_fields=['url'])
                fixed += 1

        self.stdout.write(self.style.SUCCESS(f'Done — {fixed} notification(s) updated.'))
