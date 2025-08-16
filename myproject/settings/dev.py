from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-7_o#j1q_z-u_^!z48f))@6#bg_yyaun6$n*0ip=jhr*_vx=3wi"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# NYC API Keys - Properly organized by service
# Geoclient API (for building ID lookup)
NYC_GEOCLIENT_APP_ID = "04304356a107449aa1656f9e6be87533"  # Geoclient User Primary Key
NYC_GEOCLIENT_APP_KEY = "f35ede6b69904a1fb4f9180c0408a3fb"  # Geoclient User Secondary Key

# HPD DataFeed API (for violations, bedbug reports, litigation)
NYC_HPD_API_KEY = "401655e9d4ae48b58fb867b62efa1543"  # HPD DataFeed Primary Key

# 311 Public API (for 311 complaints)
NYC_311_API_KEY = "c2a45eb9ba03409d8f8a8af178474076"  # NYC 311 Public API Primary Key

# Static files settings
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

try:
    from .local import *
except ImportError:
    pass
