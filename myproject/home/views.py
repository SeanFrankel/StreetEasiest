from django.http import JsonResponse
import json
import requests
from django.conf import settings

def get_dashboard_data(request):
    """Handle AJAX requests for NYC aggregated dashboard data."""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        address = request.GET.get('address', '')
        zip_code = request.GET.get('zip_code', '')
        
        if not address or not zip_code:
            return JsonResponse({
                'success': False,
                'error': 'Address and ZIP code are required'
            })
        
        try:
            # Replace with actual API call to NYC Open Data or your data source
            # For demo purposes, I'm creating mock data
            data = {
                'building_info': {
                    'address': address,
                    'zip_code': zip_code,
                    'borough': get_borough_from_zip(zip_code),
                    'year_built': 1985,  # Mock data
                    'units': 45,  # Mock data
                },
                'violations': {
                    'total': 12,  # Mock data
                    'open': 3,  # Mock data
                    'categories': {
                        'heat': 2,
                        'plumbing': 1,
                        'electrical': 0
                    }
                },
                'rent_info': {
                    'rent_stabilized': True,  # Mock data
                    'median_rent': '$2,450',  # Mock data
                    'neighborhood_avg': '$2,650'  # Mock data
                }
            }
            
            return JsonResponse({
                'success': True,
                'data': data
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request'
    })

def get_borough_from_zip(zip_code):
    """Helper function to determine borough from ZIP code."""
    # Basic logic - this should be expanded with actual ZIP code mapping
    zip_int = int(zip_code)
    if 10001 <= zip_int <= 10282:
        return "Manhattan"
    elif 10301 <= zip_int <= 10314:
        return "Staten Island"
    elif 11201 <= zip_int <= 11256:
        return "Brooklyn"
    elif 10451 <= zip_int <= 10475:
        return "Bronx"
    elif 11101 <= zip_int <= 11697:
        return "Queens"
    else:
        return "Unknown" 