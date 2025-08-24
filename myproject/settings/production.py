from .base import *  # noqa

DEBUG = False


# Security configuration

ROOT_URLCONF = 'myproject.urls'

# Ensure that the session cookie is only sent by browsers under an HTTPS connection.
# https://docs.djangoproject.com/en/stable/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = True

# Ensure that the CSRF cookie is only sent by browsers under an HTTPS connection.
# https://docs.djangoproject.com/en/stable/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True

# Allow the redirect importer to work in load-balanced / cloud environments.
# https://docs.wagtail.io/en/v2.13/reference/settings.html#redirects
WAGTAIL_REDIRECTS_FILE_STORAGE = "cache"

# Force HTTPS redirect (enabled by default!)
SECURE_SSL_REDIRECT = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "no-referrer-when-downgrade"

# NYC API Keys - Properly organized by service
# Geoclient API (for building ID lookup)
NYC_GEOCLIENT_APP_ID = "04304356a107449aa1656f9e6be87533"  # Geoclient User Primary Key
NYC_GEOCLIENT_APP_KEY = "f35ede6b69904a1fb4f9180c0408a3fb"  # Geoclient User Secondary Key

# HPD DataFeed API (for violations, bedbug reports, litigation)
NYC_HPD_API_KEY = "401655e9d4ae48b58fb867b62efa1543"  # HPD DataFeed Primary Key

# 311 Public API (for 311 complaints)
NYC_311_API_KEY = "c2a45eb9ba03409d8f8a8af178474076"  # NYC 311 Public API Primary Key
