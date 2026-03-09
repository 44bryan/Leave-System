from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Employee, Department


class EmployeeInline(admin.StackedInline):
    model = Employee
    can_delete = False
    verbose_name_plural = 'Employee Profile'
    fields = ['employee_id', 'department', 'role', 'supervisor', 'position', 'phone', 'date_joined_company', 'is_active']


class CustomUserAdmin(UserAdmin):
    inlines = [EmployeeInline]


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['get_full_name', 'employee_id', 'department', 'role', 'position', 'is_active']
    list_filter = ['role', 'department', 'is_active']
    search_fields = ['user__first_name', 'user__last_name', 'employee_id']

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Name'
