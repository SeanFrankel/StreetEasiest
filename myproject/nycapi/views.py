# views.py
import logging
import requests
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# NYC GeoClient API credentials
NYC_APP_ID  = '04304356a107449aa1656f9e6be87533'
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
        z = int(zip_code)
        for borough, zips in borough_map.items():
            if z in zips:
                return borough.title()
    except Exception as e:
        logger.error(f"Error determining borough: {e}")
    return None


def api_get(url, params=None, headers=None, timeout=10):
    """Helper for GET requests with error handling."""
    try:
        headers = headers or {}
        # Optionally: headers["X-App-Token"] = settings.SOCRATA_APP_TOKEN
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"API call to {url} failed: {resp.status_code}")
    except Exception as e:
        logger.error(f"API exception: {e}")
    return None


def get_building_id(address, zip_code):
    """
    Returns a tuple (BIN, BBL) for the given address via GeoClient,
    authenticating with the subscription key.
    """
    parts = address.strip().split()
    if len(parts) < 2:
        logger.error("Invalid address format")
        return None, None
    house_number = parts[0]
    street       = " ".join(parts[1:])
    borough      = get_borough_from_zip(zip_code)
    if not borough:
        logger.error("Cannot determine borough for ZIP %s", zip_code)
        return None, None

    url = "https://api.nyc.gov/geo/geoclient/v2/address"
    params = {
        "houseNumber": house_number,
        "street": street,
        "borough": borough,
        "zip": zip_code,
        "app_id": NYC_APP_ID
    }
    # Geoclient requires the subscription key header
    headers = {"Ocp-Apim-Subscription-Key": NYC_APP_KEY}
    data = api_get(url, params=params, headers=headers, timeout=10)
    if data and data.get("address"):
        addr = data["address"]
        bin_ = addr.get("buildingIdentificationNumber")
        bbl  = addr.get("bbl")
        return bin_, bbl
    return None, None
    house_number = parts[0]
    street       = " ".join(parts[1:])
    borough      = get_borough_from_zip(zip_code)
    if not borough:
        logger.error("Cannot determine borough for ZIP %s", zip_code)
        return None, None

    url = "https://api.nyc.gov/geo/geoclient/v2/address"
    params = {
        "houseNumber": house_number,
        "street": street,
        "borough": borough,
        "zip": zip_code,
        "app_id": NYC_APP_ID,
        "app_key": NYC_APP_KEY
    }
    data = api_get(url, params=params)
    if data and data.get("address"):
        addr = data["address"]
        bin_ = addr.get("buildingIdentificationNumber")
        bbl  = addr.get("bbl")
        return bin_, bbl
    return None, None


def get_hpd_violations(bin_number):
    if not bin_number:
        return [], 0
    url = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
    # first get the total count
    count_params = {
        "$query": f"SELECT count(*) WHERE bin='{bin_number}'"
    }
    count_result = api_get(url, params=count_params, timeout=20)
    total_count = int(count_result[0]['count']) if count_result else 0
 
    # now get the data
    params = {
        "$where": f"bin='{bin_number}'",
        "$order": "inspectiondate DESC",
        "$limit": 50
    }

    data = api_get(url, params=params, timeout=20)
    return data or [], total_count


def get_311_complaints(bbl):
    """
    Fetch 311 complaints using only the BBL.
    """
    if not bbl:
        return [], 0
    url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

    # first get the total count
    count_params = {
        "$query": f"SELECT count(*) WHERE bbl='{bbl}'"
    }
    count_result = api_get(url, params=count_params, timeout=20)
    total_count = int(count_result[0]['count']) if count_result else 0
 
    # now get the data

    params = {
        "$where": f"bbl='{bbl}'",
        "$order": "created_date DESC",
        "$limit": 50
    }

    data = api_get(url, params=params, timeout=20)
    return data or [], total_count

def get_bedbug_reports(bin_number):
    if not bin_number:
        return [], 0
    url = "https://data.cityofnewyork.us/resource/wz6d-d3jb.json"
    # first get the total count
    count_params = {
        "$query": f"SELECT count(*) WHERE bin='{bin_number}'"
    }
    count_result = api_get(url, params=count_params, timeout=20)
    total_count = int(count_result[0]['count']) if count_result else 0
 
    # now get the data
    params = {"$where": f"bin='{bin_number}'", "$order": "filing_date DESC", "$limit": 50}
    data = api_get(url, params=params, timeout=20) or []
    return data or [], total_count


def get_housing_litigation(bin_number):
    if not bin_number:
        return [], 0
    url = "https://data.cityofnewyork.us/resource/59kj-x8nc.json"
    # first get the total count
    count_params = {
        "$query": f"SELECT count(*) WHERE bin='{bin_number}'"
    }
    count_result = api_get(url, params=count_params, timeout=20)
    total_count = int(count_result[0]['count']) if count_result else 0
 
    # now get the data
    params = {"$where": f"bin='{bin_number}'", "$order": "caseopendate DESC", "$limit": 50}
    data = api_get(url, params=params, timeout=20) or []
    return data or [], total_count


def building_lookup_view(request):
    address  = request.GET.get("address", "").strip()
    zip_code = request.GET.get("zip_code", "").strip()
    if not address or not zip_code:
        return JsonResponse({"success": False, "error": "Address and ZIP code are required."})

    bin_number, bbl = get_building_id(address, zip_code)

    violations, hpd_total = get_hpd_violations(bin_number)
    complaints, complaints_total = get_311_complaints(bbl)
    bedbugs, bedbugs_total = get_bedbug_reports(bin_number)
    housing_lits, housing_total = get_housing_litigation(bin_number)

    result = {
        "address": address,
        "zip_code": zip_code,
        "building_id": bin_number,
        "bbl": bbl,
        "hpd_violations": violations,
        "hpd_violations_total_count": hpd_total,
        "complaints": complaints,
        "complaints_total_count": complaints_total,
        "bedbug_reports": bedbugs,
        "bedbug_reports_total_count": bedbugs_total,
        "litigation": housing_lits,
        "litigation_total_count": housing_total,
    }
    return JsonResponse({"success": True, "data": result})