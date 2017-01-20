from caching.base import CachingMixin, CachingManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.core import validators
from django.db import models
from django.utils.translation import ugettext_lazy as _
import re
from django.utils import timezone
from django.utils.http import urlquote
from django.core.mail import send_mail


class DwwenUserManager(UserManager):

    def get_by_username(self, username):
        return self.get(username__iexact=username)

    def get_by_natural_key(self, username):
        if '@' in username:
            return self.get_by_email(username)
        return self.get_by_username(username)

    def get_by_email(self, email):
        return self.get(email__iexact=email)

    def filter(self, **kwargs):
        if 'username' in kwargs:
            kwargs['username__iexact'] = kwargs['username']
            del kwargs['username']

        if 'email' in kwargs:
            kwargs['email__iexact'] = kwargs['email']
            del kwargs['email']

        return super(DwwenUserManager, self).filter(**kwargs)

    def get(self, **kwargs):
        if 'username' in kwargs:
            kwargs['username__iexact'] = kwargs['username']
            del kwargs['username']

        if 'email' in kwargs:
            kwargs['email__iexact'] = kwargs['email']
            del kwargs['email']

        return super(DwwenUserManager, self).get(**kwargs)


class DwwenUser(AbstractBaseUser, PermissionsMixin):
    """
    A class implementing a fully featured User model with
    admin-compliant permissions.

    Username, password and email are required. Other fields are optional.
    """
    username = models.CharField(_('username'), max_length=15, unique=True,
        help_text=_('Required. 15 characters or fewer. Letters, numbers and underscore'),
        validators=[
            validators.RegexValidator(re.compile('^[a-zA-Z0-9_]+$'), _('Enter a valid username.'), 'invalid')
        ])
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
    email = models.EmailField(_('email address'), blank=False, unique=True)
    is_staff = models.BooleanField(_('staff status'), default=False,
        help_text=_('Designates whether the user can log into this admin '
                    'site.'))
    is_active = models.BooleanField(_('active'), default=True,
        help_text=_('Designates whether this user should be treated as '
                    'active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = DwwenUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def get_absolute_url(self):
        return "/users/%s/" % urlquote(self.username)

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

    def email_user(self, subject, message, from_email=None):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email])


class UserProfile(models.Model):
    user = models.OneToOneField('DwwenUser', related_name='profile')
    is_email_verified = models.BooleanField(default=False)
    email_verfication_code = models.CharField(max_length=300, blank=True)


class Device(models.Model):

    IOS = 1
    ANDROID = 2
    TYPE_CHOICES = (
        (IOS, 'iOS'),
        (ANDROID, 'Android')
    )

    ACTIVE = 1
    INACTIVE = 2
    STATUS_CHOICES = (
        (ACTIVE, _('Active')),
        (INACTIVE, _('Inactive'))
    )

    type = models.SmallIntegerField(choices=TYPE_CHOICES)
    key = models.CharField(max_length=300) #TODO just guessing
    is_enabled = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    last_update_date = models.DateTimeField(auto_now=True)
    user = models.ForeignKey('DwwenUser', related_name='devices')
    status = models.SmallIntegerField(choices=STATUS_CHOICES)
