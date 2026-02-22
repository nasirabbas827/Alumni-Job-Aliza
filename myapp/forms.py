from django import forms
from django.contrib.auth.hashers import make_password , check_password
from .models import RegisteredUsers

class RegisterForm(forms.ModelForm):
    # Manually defined fields for custom widgets and labels
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create password'
        }),
        label="Password",
        required=True
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        }),
        label="Confirm Password",
        required=True
    )

    class Meta:
        model = RegisteredUsers
        fields = [
            'full_name',
            'email',
            'username',
            'role',
            'gender',
            'password', 
        ]

        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control', 'style': 'padding: 8px 12px;'}),
            'gender': forms.Select(attrs={'class': 'form-control', 'style': 'padding: 8px 12px;'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if RegisteredUsers.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if RegisteredUsers.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already taken.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        # Validation for matching passwords
        if password and confirm_password:
            if password != confirm_password:
                self.add_error('confirm_password', "Passwords do not match.")
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        # Encrypt the password before saving
        user.password = make_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Email'
        }),
        label="Email"
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Password'
        }),
        label="Password"
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            try:
                # Use filter().first() to avoid unhandled DoesNotExist errors inside clean
                user = RegisteredUsers.objects.filter(email=email).first()
                
                if not user:
                    raise forms.ValidationError("Invalid email or password.")
                
                if not check_password(password, user.password):
                    raise forms.ValidationError("Invalid email or password.")

                if user.status != 'active':
                    raise forms.ValidationError("Account is inactive.")
                
                cleaned_data["user"] = user
            except Exception:
                raise forms.ValidationError("An error occurred during login.")

        return cleaned_data
    

from django import forms
from .models import Profile

class UpdateProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'linkedin_url',
            'education',
            'experience',
            'skills',
            'resume',
            'profile_picture',
            'is_public'
        ]

        widgets = {
            'linkedin_url': forms.URLInput(attrs={'class': 'form-control'}),
            'education': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'experience': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'skills': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

from .models import Job

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        exclude = ['employer', 'status', 'created_at']

        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'salary_min': forms.NumberInput(attrs={'class': 'form-control'}),
            'salary_max': forms.NumberInput(attrs={'class': 'form-control'}),
            'job_type': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'skills_required': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


# forms.py
from django import forms
from .models import JobApplication

class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['resume']
        widgets = {
            'resume': forms.FileInput(attrs={'class': 'form-control'}),
        }