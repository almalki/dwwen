from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from auth.forms import UserChangeForm, UserCreationForm, AdminPasswordChangeForm
from auth.models import DwwenUser


class DwwenUserAdmin(UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2')}
        ),
    )


#admin.site.unregister(User)
admin.site.register(DwwenUser, DwwenUserAdmin)