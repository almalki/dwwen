from django.contrib.auth.forms import ReadOnlyPasswordHashField, SetPasswordForm as AuthSetPasswordForm
from django import forms
from django.utils.translation import ugettext_lazy as _
from api.utils import check_username
from auth.models import DwwenUser

__author__ = 'abdulaziz'


class UserCreationForm(forms.Form):
    """
    A form that creates a user, with no privileges, from the given username and
    password.
    """
    error_messages = {
        'duplicate_username': _("A user with that username already exists."),
        'duplicate_email': _("A user with that email already exists."),
        'password_mismatch': _("The two password fields didn't match."),
    }
    username = forms.RegexField(label=_("Username"), max_length=15, min_length=3,
        regex=r'^[a-zA-Z0-9_]+$',
        help_text=_("Required. 15 characters or fewer. Letters, numbers and underscore."),
        error_messages={
            'invalid': _("This value may contain only letters, numbers and underscore.")})
    email = forms.EmailField(required=True, label=_("Email"), min_length=1)
    password1 = forms.CharField(label=_("Password"), min_length=8,
        widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"), min_length=8,
        widget=forms.PasswordInput)

    def clean_username(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        username = self.cleaned_data["username"]
        try:
            DwwenUser.objects.get(username__iexact=username)
        except DwwenUser.DoesNotExist:
            return username
        raise forms.ValidationError(
            self.error_messages['duplicate_username'],
            code='duplicate_username',
        )

    def clean_email(self):
        # Since User.email is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        email = self.cleaned_data["email"]
        try:
            DwwenUser.objects.get(email__iexact=email)
        except DwwenUser.DoesNotExist:
            return email
        raise forms.ValidationError(
            self.error_messages['duplicate_email'],
            code='duplicate_email',
        )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2

    def save(self, commit=True):
        username = self.cleaned_data["username"]
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password1"]
        user = DwwenUser.objects.create_user(username, email=email, password=password)
        return user

    def save_m2m(self):
        pass


class UserChangeForm(forms.ModelForm):
    username = forms.RegexField(
        label=_("Username"), max_length=15, regex=r"^[a-zA-Z0-9_]+$", min_length=3,
        help_text=_("Required. 15 characters or fewer. Letters, digits and underscore."),
        error_messages={
            'invalid': _("This value may contain only letters, numbers and underscore")})
    password = ReadOnlyPasswordHashField(label=_("Password"),
        help_text=_("Raw passwords are not stored, so there is no way to see "
                    "this user's password, but you can change the password "
                    "using <a href=\"password/\">this form</a>."))

    class Meta:
        model = DwwenUser
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(UserChangeForm, self).__init__(*args, **kwargs)
        f = self.fields.get('user_permissions', None)
        if f is not None:
            f.queryset = f.queryset.select_related('content_type')

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


class AdminPasswordChangeForm(forms.Form):
    """
    A form used to change the password of a user in the admin interface.
    """
    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }
    password1 = forms.CharField(label=_("Password"), min_length=8,
                                widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password (again)"), min_length=8,
                                widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(AdminPasswordChangeForm, self).__init__(*args, **kwargs)

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )
        return password2

    def save(self, commit=True):
        """
        Saves the new password.
        """
        self.user.set_password(self.cleaned_data["password1"])
        if commit:
            self.user.save()
        return self.user

    def _get_changed_data(self):
        data = super(AdminPasswordChangeForm, self).changed_data
        for name in self.fields.keys():
            if name not in data:
                return []
        return ['password']
    changed_data = property(_get_changed_data)
    
    
class SetPasswordForm(AuthSetPasswordForm):
    """
    A form that lets a user change set their password without entering the old
    password
    """
    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }
    new_password1 = forms.CharField(label=_("New password"), required=True, min_length=8,
                                    widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("New password confirmation"), required=True, min_length=8,
                                    widget=forms.PasswordInput)


class SignupForm(UserCreationForm):
    def clean_username(self):
        username = super(SignupForm, self).clean_username()
        check_username(username)
        return username