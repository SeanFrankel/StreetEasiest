from django.utils.cache import patch_response_headers
from django.utils.deprecation import MiddlewareMixin

class PageCacheMiddleware(MiddlewareMixin):
    """
    Middleware to cache Wagtail pages for improved performance
    """
    def process_response(self, request, response):
        # Only cache GET requests
        if request.method != 'GET':
            return response
            
        # Don't cache admin or authenticated pages
        if request.path.startswith('/admin/') or request.user.is_authenticated:
            return response
            
        # Cache for 5 minutes by default
        patch_response_headers(response, cache_timeout=300)
        return response 