from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import Employee, Department


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Employee ID or Username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Password',
        })
    )


class EmployeeCreateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_username'}),
        help_text='Auto-generated from first name. You may change it.',
    )
    password = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'background:#f8fafc;color:#6b7a8d;cursor:not-allowed;',
            'value': 'Micei2021',
        }),
        initial='Micei2021',
        help_text='Default password. Employee must change it on first login.',
    )

    # Contract fields (required at registration)
    CONTRACT_TYPE_CHOICES = [
        ('CDI',    'CDI — Permanent'),
        ('CDD',    'CDD — Fixed Term'),
        ('INTERN', 'Internship Contract'),
        ('WACS',   'WACS Residency / Trainee Programme'),
    ]
    contract_type = forms.ChoiceField(
        choices=CONTRACT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_contract_type'}),
        label='Contract Type',
    )
    contract_start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Contract Start Date',
    )
    contract_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_contract_end_date'}),
        label='Contract End Date',
        help_text='Required for CDD, INTERN and WACS.',
    )
    class Meta:
        model = Employee
        fields = ['employee_id', 'department', 'role', 'staff_category', 'supervisor', 'unit_head', 'position', 'phone', 'date_joined_company', 'date_of_birth', 'sex', 'nationality', 'contract_number', 'qualifications', 'school_name', 'speciality', 'signature']
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select', 'id': 'id_role'}),
            'staff_category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 5, 12, 12A, 12AB', 'style': 'text-transform:uppercase;'}),
            'supervisor': forms.Select(attrs={'class': 'form-select'}),
            'unit_head': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'date_joined_company': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sex': forms.Select(attrs={'class': 'form-select'}),
            'nationality': forms.TextInput(attrs={'class': 'form-control'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CTR-2024-001'}),
            'qualifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'school_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. University of Yaoundé I'}),
            'speciality': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Medicine, Nursing, Ophthalmology'}),
            'signature': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
        }

    def clean_staff_category(self):
        value = self.cleaned_data.get('staff_category', '').strip().upper()
        return value

    def clean(self):
        cleaned = super().clean()
        ct = cleaned.get('contract_type')
        end = cleaned.get('contract_end_date')
        if ct in ('CDD', 'INTERN', 'WACS') and not end:
            self.add_error('contract_end_date', 'End date is required for this contract type.')
        return cleaned

    def save(self, commit=True):
        employee = super().save(commit=False)
        user = User(
            username=self.cleaned_data['username'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data['email'],
        )
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            employee.user = user
            employee.save()
        return employee


class EmployeeEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Employee
        fields = ['employee_id', 'department', 'role', 'staff_category', 'supervisor', 'unit_head', 'position', 'phone', 'date_joined_company', 'date_of_birth', 'sex', 'nationality', 'contract_number', 'qualifications', 'school_name', 'speciality', 'is_active', 'signature']
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'staff_category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 5, 12, 12A, 12AB', 'style': 'text-transform:uppercase;'}),
            'supervisor': forms.Select(attrs={'class': 'form-select'}),
            'unit_head': forms.Select(attrs={'class': 'form-select'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'date_joined_company': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'sex': forms.Select(attrs={'class': 'form-select'}),
            'nationality': forms.TextInput(attrs={'class': 'form-control'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control'}),
            'qualifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'school_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. University of Yaoundé I'}),
            'signature': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
            'speciality': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Medicine, Nursing, Ophthalmology'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_staff_category(self):
        value = self.cleaned_data.get('staff_category', '').strip().upper()
        return value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['signature'].required = False
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        employee = super().save(commit=False)
        employee.user.first_name = self.cleaned_data['first_name']
        employee.user.last_name = self.cleaned_data['last_name']
        employee.user.email = self.cleaned_data['email']
        if commit:
            employee.user.save()
            employee.save()
        return employee


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your current password'})
    )
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'At least 8 characters'}),
        min_length=8,
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat new password'})
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        pw = self.cleaned_data.get('current_password')
        if not self.user.check_password(pw):
            raise ValidationError("Incorrect current password.")
        return pw

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save()


class AdminResetCredentialsForm(forms.Form):
    username = forms.CharField(
        label="Username",
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_password = forms.CharField(
        label="New Password",
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to keep current password'}),
        min_length=8,
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Repeat new password'})
    )

    def __init__(self, target_user, *args, **kwargs):
        self.target_user = target_user
        super().__init__(*args, **kwargs)
        self.fields['username'].initial = target_user.username

    def clean_username(self):
        uname = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username=uname).exclude(pk=self.target_user.pk).exists():
            raise ValidationError("This username is already taken by another user.")
        return uname

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password')
        p2 = cleaned.get('confirm_password')
        if p1 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")
        if p1 and len(p1) < 8:
            self.add_error('new_password', "Password must be at least 8 characters.")
        return cleaned

    def save(self):
        self.target_user.username = self.cleaned_data['username']
        if self.cleaned_data.get('new_password'):
            self.target_user.set_password(self.cleaned_data['new_password'])
        self.target_user.save()


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'code']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
        }
