from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-7_o#j1q_z-u_^!z48f))@6#bg_yyaun6$n*0ip=jhr*_vx=3wi"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# NYC API Key for HPD Datafeed API
NYC_API_KEY = "f35ede6b69904a1fb4f9180c0408a3fb"  # Replace with your actual API key

# Static files settings
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

try:
    from .local import *
except ImportError:
    pass
