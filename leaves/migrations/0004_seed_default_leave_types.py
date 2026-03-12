from django.db import migrations

DEFAULT_LEAVE_TYPES = [
    {'name': 'Annual Leave',                'is_deductible': True,  'color': 'primary',   'requires_document': False},
    {'name': 'Permission',                  'is_deductible': True,  'color': 'warning',   'requires_document': False},
    {'name': 'Permission for School Leave', 'is_deductible': True,  'color': 'info',      'requires_document': True},
    {'name': 'Sick Leave',                  'is_deductible': False, 'color': 'danger',    'requires_document': True},
    {'name': 'Maternity Leave',             'is_deductible': False, 'color': 'success',   'requires_document': True},
    {'name': 'Paternity Leave',             'is_deductible': False, 'color': 'success',   'requires_document': True},
    {'name': 'Marriage Leave',              'is_deductible': False, 'color': 'secondary', 'requires_document': False},
    {'name': 'Compassionate Leave',         'is_deductible': False, 'color': 'dark',      'requires_document': False},
    {'name': 'Study Leave',                 'is_deductible': False, 'color': 'secondary', 'requires_document': False},
]


def seed_leave_types(apps, schema_editor):
    LeaveType = apps.get_model('leaves', 'LeaveType')
    for lt in DEFAULT_LEAVE_TYPES:
        LeaveType.objects.get_or_create(
            name=lt['name'],
            defaults={
                'is_deductible':     lt['is_deductible'],
                'color':             lt['color'],
                'requires_document': lt['requires_document'],
                'is_active':         True,
                'description':       '',
            }
        )


def unseed_leave_types(apps, schema_editor):
    # Reverse: remove only those that have no linked leave requests
    LeaveType = apps.get_model('leaves', 'LeaveType')
    names = [lt['name'] for lt in DEFAULT_LEAVE_TYPES]
    LeaveType.objects.filter(name__in=names, leaverequest=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('leaves', '0003_add_is_deductible_to_leavetype'),
    ]

    operations = [
        migrations.RunPython(seed_leave_types, unseed_leave_types),
    ]
