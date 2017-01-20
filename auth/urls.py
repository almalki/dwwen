from django.conf.urls import patterns, url
from django.contrib.auth.views import password_reset_confirm, password_reset_complete, password_reset
from django.views.generic.base import TemplateView
from django.contrib.auth import views as auth_views
from auth.forms import SetPasswordForm

__author__ = 'abdulaziz'


urlpatterns = patterns('auth.views',
    url(r'^signup/$', 'signup', name='signup'),
    url(r'^signup-thanks/$', TemplateView.as_view(template_name='accounts/signup-thanks.html'), name='signup-thanks'),
    url(r'^login/$', auth_views.login, {'template_name': 'accounts/login.html'}, name='auth_login'),
    url(r'^logout/$', auth_views.logout, {'next_page': 'home', }, name='auth_logout'),

    url(r'^password/reset/key/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/$', password_reset_confirm,
        kwargs={'template_name': 'accounts/password_reset_confirm.html', 'set_password_form': SetPasswordForm},
        name='password_reset_confirm'),

    url(r"^password/reset/complete/$", password_reset_complete,
        kwargs={'template_name': 'accounts/password_reset_complete.html'},name="password_reset_complete"),

)