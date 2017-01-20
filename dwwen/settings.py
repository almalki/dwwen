"""
Django settings for dwwen project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from django.conf import settings, global_settings

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'gv6h&0y5!*2)&%en0j7a&f(a4orga1sw#6_(hp%n5lqu&)k+z='

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = []


SECRET_RESERVED_USERNAMES = ('dwwen', 'admin', 'django', 'redis', 'postgres', 'postgresql')

NOT_ALLOWED_TOKENS = ('dwwen', 'admin',)

LANGUAGE_CODE = 'ar'

LOGIN_REDIRECT_URL = 'web-blog-list'

EMAIL_HOST = 'smtp.mailgun.org'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 587
EMAIL_USE_TLS = True


FROM_DWWEN_EMAIL = 'noreply@dwwen.com'

CACHE_COUNT_TIMEOUT = 900


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'provider',
    'provider.oauth2',
    'api',
    'cities_light',
    'rest_framework',
    'south',
    'django_rq',
    'django_rq_dashboard',
    'scraper',
    'rest_framework_swagger',
    'bootstrap3',
    'sorl.thumbnail',
    'markdown_deux',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'api.middleware.SetRemoteAddrFromRealIp'
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
)

ROOT_URLCONF = 'dwwen.urls'

WSGI_APPLICATION = 'dwwen.wsgi.application'

AUTH_USER_MODEL = 'auth.DwwenUser'

TEMPLATE_DIRS = (os.path.join(BASE_DIR, 'templates').replace('\\','/'),)

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale').replace('\\','/'),
)

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static').replace('\\','/'),
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)


AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

TIME_ZONE = 'Asia/Riyadh'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

MEDIA_ROOT = os.path.join(BASE_DIR, '..', 'media').replace('\\','/')

RQ_QUEUES = {
    'default': {
        'HOST': 'localhost',
        'PORT': 6379,
        'DB': 0,
    }
}

BLOGS_SOLR_URL = 'http://localhost:8983/solr/blogs'
POSTS_SOLR_URL = 'http://localhost:8983/solr/posts'
BOILERPIPE_URL = "http://services.prod.dwwen.com:8090/"

REST_FRAMEWORK = {
    'PAGINATE_BY': 20,                 # Default to 10
    'PAGINATE_BY_PARAM': 'count',  # Allow client to override, using `?count=xxx`.
    'MAX_PAGINATE_BY': 100,             # Maximum limit allowed when using `?count=xxx`.
    'DEFAULT_PAGINATION_SERIALIZER_CLASS': 'api.serializers.DwwenPaginationSerializer',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.OAuth2Authentication',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'api.throttles.BurstRateThrottle',
        'api.throttles.SustainedRateThrottle'
    ),
    'DEFAULT_THROTTLE_RATES': {
        'burst': '60/min',
        'sustained': '5000/day'
    },
}

import datetime
OAUTH_EXPIRE_DELTA = datetime.timedelta(days=7)
OAUTH_ENFORCE_SECURE = True

SWAGGER_SETTINGS = {
    "exclude_namespaces": [],  # List URL namespaces to ignore
    "api_version": '1.0',  # Specify your API's version
    "api_path": "/",  # Specify the path to your API not a root level
    "enabled_methods": [  # Specify which methods to enable in Swagger UI
        'get',
        'post',
        'put',
        'patch',
        'delete'
    ],
    "api_key": '',  # An API key
    "is_authenticated": False,  # Set to True to enforce user authentication,
    "is_superuser": False,  # Set to True to enforce admin only access
}

try:
    LOCAL_SETTINGS
except NameError:
    try:
        from local_settings import *
    except ImportError:
        pass