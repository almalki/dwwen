from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^v1/', include('api.urls')),
    url(r'^', include('dwwen_web.urls')),
    url(r'^admin/rq/', include('django_rq_dashboard.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^oauth2/', include('provider.oauth2.urls', namespace='oauth2')),
    url(r'^accounts/', include('auth.urls')),

)+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) +\
              static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += staticfiles_urlpatterns()