import json
import logging
import os
import urllib.parse
import requests
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# NYC GeoClient API credentials
NYC_APP_ID = '04304356a107449aa1656f9e6be87533'
NYC_APP_KEY = 'f35ede6b69904a1fb4f9180c0408a3fb'

def get_borough_from_zip(zip_code):
    borough_map = {
        'MANHATTAN': list(range(10001, 10283)) + [10292],
        'BRONX': list(range(10451, 10476)),
        'BROOKLYN': list(range(11201, 11257)) + [11351],
        'QUEENS': list(range(11004, 11110)) + list(range(11351, 11698)),
        'STATEN ISLAND': list(range(10301, 10315))
    }
    try:
        zip_num = int(zip_code)
        for borough, zips in borough_map.items():
            if zip_num in zips:
                return borough.title()
    except Exception as e:
        logger.error(f"Error determining borough: {e}")
    return None

def api_get(url, params=None, headers=None, timeout=10):
    """Helper for GET requests with error handling."""
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API call to {url} failed with status {response.status_code}")
    except Exception as e:
        logger.error(f"API call exception: {e}")
    return None

def get_building_id(address, zip_code):
    """
    Retrieve the building ID using the NYC GeoClient API.
    Assumes address is in "house_number street" format.
    """
    parts = address.strip().split()
    if len(parts) < 2:
        logger.error("Invalid address format")
        return None
    house_number = parts[0]
    street = " ".join(parts[1:])
    borough = get_borough_from_zip(zip_code)
    if not borough:
        logger.error("Borough could not be determined")
        return None
    url = "https://api.nyc.gov/geo/geoclient/v2/address"
    params = {
        "houseNumber": house_number,
        "street": street,
        "borough": borough,
        "zip": zip_code
    }
    headers = {
        "Ocp-Apim-Subscription-Key": NYC_APP_KEY,
        "X-App-ID": NYC_APP_ID
    }
    data = api_get(url, params=params, headers=headers, timeout=10)
    if data and "address" in data:
        return data["address"].get("buildingIdentificationNumber")
    return None

def get_hpd_violations(building_id):
    """Fetch HPD violations using a single NYC Open Data endpoint."""
    url = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
    params = {"$where": f"bin='{building_id}'", "$order": "inspectiondate DESC", "$limit": 50}
    data = api_get(url, params=params, timeout=10)
    return data if data else []

def get_311_complaints(address, zip_code, building_id=None):
    url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
    headers = {}
    if building_id:
        # 311 data might store bin or building_id differently; try both if needed
        params = {
            "$where": f"building_id='{building_id}'",  # or bin='{building_id}' if the 311 dataset uses bin
            "$order": "created_date DESC",
            "$limit": 50
        }
    else:
        house_number = address.split()[0] if address.split() else ""
        params = {
            "$where": f"incident_zip='{zip_code}' AND incident_address like '{house_number}%'",
            "$order": "created_date DESC",
            "$limit": 50
        }
    return api_get(url, params=params, headers=headers, timeout=10) or []


def get_bedbug_reports(building_id):
    """Fetch bedbug reports using the building ID (BIN)."""
    url = "https://data.cityofnewyork.us/resource/wz6d-d3jb.json"
    params = {"$where": f"bin='{building_id}'", "$order": "filing_date DESC", "$limit": 50}
    data = api_get(url, params=params, timeout=10)
    return data if data else []


def get_housing_litigation(bin_number):
    if not bin_number:
        return []
    url = "https://data.cityofnewyork.us/resource/59kj-x8nc.json"
    headers = {}
    # If bin is text in SoQL, use quotes:
    params = {
        "$where": f"bin='{bin_number}'",   # all-lowercase 'bin', in quotes
        "$order": "caseopendate DESC",
        "$limit": 50
    }
    return api_get(url, params=params, headers=headers, timeout=10) or []

def building_lookup_view(request):
    """
    Main AJAX view.
    Retrieves the building ID, then fetches HPD violations, 311 complaints,
    bedbug reports, and housing litigation records.
    """
    address = request.GET.get("address", "").strip()
    zip_code = request.GET.get("zip_code", "").strip()
    if not address or not zip_code:
        return JsonResponse({"success": False, "error": "Address and ZIP code are required."})
    
    building_id = get_building_id(address, zip_code)
    hpd_violations = get_hpd_violations(building_id) if building_id else []
    complaints = get_311_complaints(address, zip_code, building_id)
    bedbug_reports = get_bedbug_reports(building_id) if building_id else []
    litigation = get_housing_litigation(building_id) if building_id else []
    
    result = {
        "address": address,
        "zip_code": zip_code,
        "building_id": building_id,
        "hpd_violations": hpd_violations,
        "complaints": complaints,
        "bedbug_reports": bedbug_reports,
        "litigation": litigation,
    }
    return JsonResponse({"success": True, "data": result})