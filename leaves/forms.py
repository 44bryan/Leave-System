from django import forms
from .models import LeaveRequest, LeaveType


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'supporting_document']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control form-control-lg', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control form-control-lg', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Please provide the reason for your leave request...'}),
            'supporting_document': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['leave_type'].queryset = LeaveType.objects.filter(is_active=True)
        _date_formats = [
            '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y',
            '%m/%d/%Y', '%m-%d-%Y', '%Y/%m/%d',
            '%d %m %Y', '%d.%m.%Y',
        ]
        self.fields['start_date'].input_formats = _date_formats
        self.fields['end_date'].input_formats = _date_formats

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and start_date.weekday() >= 5:
            self.add_error('start_date', "Start date cannot be a Saturday or Sunday.")

        if end_date and end_date.weekday() >= 5:
            self.add_error('end_date', "End date cannot be a Saturday or Sunday.")

        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError("End date cannot be before start date.")

        return cleaned_data


class ApprovalForm(forms.Form):
    action = forms.ChoiceField(choices=[('approve', 'Approve'), ('reject', 'Reject')])
    remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional remarks...'}),
        label='Remarks'
    )
