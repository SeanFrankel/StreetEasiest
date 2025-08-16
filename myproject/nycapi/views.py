# views.py
import logging
import requests
import time
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# NYC GeoClient API credentials (now using settings)
# These are kept for backward compatibility but should use settings instead


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


def api_get(url, params=None, headers=None, timeout=10, retries=2):
    """Helper for GET requests with error handling and retry logic."""
    headers = headers or {}
    # Add User-Agent to avoid being blocked
    headers["User-Agent"] = "StreetEasiest/1.0 (NYC Data Lookup Tool)"
    
    # NYC Open Data APIs work without authentication for basic queries
    # Commenting out API key authentication as it's causing 403 errors
    # Most NYC APIs have generous rate limits without requiring authentication
    logger.info(f"Making API call to {url} without authentication")
    
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            
            # Log details for debugging
            logger.info(f"API call to {url} - Status: {resp.status_code}, Attempt: {attempt + 1}")
            
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in [503, 429]:  # Rate limited or service unavailable
                if attempt < retries:
                    wait_time = (2 ** attempt) + 1  # Exponential backoff: 2, 5, 9 seconds
                    logger.warning(f"Rate limited/throttled (HTTP {resp.status_code}) for {url} - Retrying in {wait_time}s (attempt {attempt + 1}/{retries + 1})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Rate limited/throttled (HTTP {resp.status_code}) for {url} - Max retries exceeded")
                    return None
            else:
                logger.error(f"API call to {url} failed: {resp.status_code} - Response: {resp.text[:200]}")
                return None
                
        except Exception as e:
            if attempt < retries:
                wait_time = (2 ** attempt) + 1
                logger.warning(f"API exception for {url}: {e} - Retrying in {wait_time}s")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"API exception for {url}: {e} - Max retries exceeded")
                return None
    
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
        "app_id": getattr(settings, 'NYC_GEOCLIENT_APP_ID', '')
    }
    # Geoclient requires the subscription key header
    headers = {"Ocp-Apim-Subscription-Key": getattr(settings, 'NYC_GEOCLIENT_APP_KEY', '')}
    data = api_get(url, params=params, headers=headers, timeout=10)
    if data and data.get("address"):
        addr = data["address"]
        bin_ = addr.get("buildingIdentificationNumber")
        bbl  = addr.get("bbl")
        return bin_, bbl
    return None, None


def get_hpd_violations(bin_number):
    if not bin_number:
        logger.warning("get_hpd_violations called with no bin_number")
        return [], 0
    url = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
    
    # Get data first, then estimate count from results
    params = {
        "$where": f"bin='{bin_number}'",
        "$order": "inspectiondate DESC",
        "$limit": 1000  # Increased limit to get more comprehensive results
    }

    logger.info(f"Making HPD API call with BIN: {bin_number}, URL: {url}, params: {params}")
    data = api_get(url, params=params, timeout=30)  # Increased timeout
    logger.info(f"HPD API returned data: {data is not None}, length: {len(data) if data else 0}")
    if not data:
        logger.warning(f"No HPD data returned for BIN: {bin_number}")
        return [], 0
        
    # If we got exactly 1000 results, there might be more - do a separate count query
    if len(data) == 1000:
        count_params = {
            "$query": f"SELECT count(*) WHERE bin='{bin_number}'"
        }
        count_result = api_get(url, params=count_params, timeout=20)
        total_count = int(count_result[0]['count']) if count_result else len(data)
    else:
        total_count = len(data)
    
    # Return only the first 50 for display, but keep the accurate total count
    return data[:50], total_count


def get_311_complaints(bbl):
    """
    Fetch 311 complaints using only the BBL.
    """
    if not bbl:
        return [], 0
    url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

    # Get data first with higher limit
    params = {
        "$where": f"bbl='{bbl}'",
        "$order": "created_date DESC",
        "$limit": 1000
    }

    data = api_get(url, params=params, timeout=30)
    if not data:
        return [], 0
        
    # If we got exactly 1000 results, there might be more
    if len(data) == 1000:
        count_params = {
            "$query": f"SELECT count(*) WHERE bbl='{bbl}'"
        }
        count_result = api_get(url, params=count_params, timeout=20)
        total_count = int(count_result[0]['count']) if count_result else len(data)
    else:
        total_count = len(data)
    
    return data[:50], total_count

def get_bedbug_reports(bin_number):
    if not bin_number:
        return [], 0
    url = "https://data.cityofnewyork.us/resource/wz6d-d3jb.json"
    
    # Get data first with higher limit
    params = {"$where": f"bin='{bin_number}'", "$order": "filing_date DESC", "$limit": 1000}
    data = api_get(url, params=params, timeout=30)
    if not data:
        return [], 0
        
    # If we got exactly 1000 results, there might be more
    if len(data) == 1000:
        count_params = {
            "$query": f"SELECT count(*) WHERE bin='{bin_number}'"
        }
        count_result = api_get(url, params=count_params, timeout=20)
        total_count = int(count_result[0]['count']) if count_result else len(data)
    else:
        total_count = len(data)
    
    return data[:50], total_count


def get_housing_litigation(bin_number):
    if not bin_number:
        return [], 0
    url = "https://data.cityofnewyork.us/resource/59kj-x8nc.json"
    
    # Get data first with higher limit
    params = {"$where": f"bin='{bin_number}'", "$order": "caseopendate DESC", "$limit": 1000}
    data = api_get(url, params=params, timeout=30)
    if not data:
        return [], 0
        
    # If we got exactly 1000 results, there might be more
    if len(data) == 1000:
        count_params = {
            "$query": f"SELECT count(*) WHERE bin='{bin_number}'"
        }
        count_result = api_get(url, params=count_params, timeout=20)
        total_count = int(count_result[0]['count']) if count_result else len(data)
    else:
        total_count = len(data)
    
    return data[:50], total_count


def get_lead_paint_violations(bin_number):
    """
    Fetch HPD Lead Paint Violations by filtering from the main HPD violations dataset.
    Try the dedicated lead paint API first, fall back to filtering if unavailable.
    """
    if not bin_number:
        return [], 0
    
    # First try the dedicated lead paint violations API
    lead_api_url = "https://data.cityofnewyork.us/resource/au8t-hgv2.json"
    
    # Try dedicated API first with optimized single request
    params = {
        "$where": f"bin='{bin_number}'",
        "$order": "inspectiondate DESC",
        "$limit": 1000
    }
    data = api_get(lead_api_url, params=params, timeout=30)
    
    if data:
        # Dedicated API is working - return results
        total_count = len(data) if len(data) < 1000 else 1000  # Estimate if we hit the limit
        return data[:50], total_count
    
    # Fall back to filtering main HPD violations dataset for lead-specific violations
    url = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
    
    # More specific lead paint filter - focus on lead-based paint hazards
    lead_filter = (
        "upper(novdescription) like upper('%lead%paint%') OR "
        "upper(novdescription) like upper('%lead%based%') OR "
        "upper(novdescription) like upper('%lead%hazard%') OR "
        "upper(novdescription) like upper('%peeling%paint%') OR "
        "upper(novdescription) like upper('%deteriorated%paint%')"
    )
    
    # Get the actual lead-related violation data with optimized request
    params = {
        "$where": f"bin='{bin_number}' AND ({lead_filter})",
        "$order": "inspectiondate DESC",
        "$limit": 1000
    }
    
    data = api_get(url, params=params, timeout=30)
    if not data:
        return [], 0
    
    # If we got exactly 1000 results, there might be more
    if len(data) == 1000:
        count_params = {
            "$query": f"SELECT count(*) WHERE bin='{bin_number}' AND ({lead_filter})"
        }
        count_result = api_get(url, params=count_params, timeout=20)
        total_count = int(count_result[0]['count']) if count_result else len(data)
    else:
        total_count = len(data)
    
    return data[:50], total_count


def building_lookup_view(request):
    address  = request.GET.get("address", "").strip()
    zip_code = request.GET.get("zip_code", "").strip()
    if not address or not zip_code:
        return JsonResponse({"success": False, "error": "Address and ZIP code are required."})

    bin_number, bbl = get_building_id(address, zip_code)
    
    if not bin_number and not bbl:
        return JsonResponse({
            "success": False, 
            "error": "Unable to find building data for this address. Please verify the address and zip code."
        })

    # Log the retrieved identifiers for debugging
    logger.info(f"Found Building ID: {bin_number}, BBL: {bbl} for {address}, {zip_code}")

    violations, hpd_total = get_hpd_violations(bin_number)
    logger.info(f"HPD Violations: Found {hpd_total} violations, returned {len(violations)} results")
    time.sleep(0.5)  # Small delay to avoid rate limiting
    
    complaints, complaints_total = get_311_complaints(bbl)
    logger.info(f"311 Complaints: Found {complaints_total} complaints, returned {len(complaints)} results")
    time.sleep(0.5)
    
    bedbugs, bedbugs_total = get_bedbug_reports(bin_number)
    logger.info(f"Bedbug Reports: Found {bedbugs_total} reports, returned {len(bedbugs)} results")
    time.sleep(0.5)
    
    housing_lits, housing_total = get_housing_litigation(bin_number)
    logger.info(f"Housing Litigation: Found {housing_total} cases, returned {len(housing_lits)} results")
    time.sleep(0.5)
    
    lead_paint, lead_paint_total = get_lead_paint_violations(bin_number)
    logger.info(f"Lead Paint Violations: Found {lead_paint_total} violations, returned {len(lead_paint)} results")

    # Check if we got any data at all
    total_records = hpd_total + complaints_total + bedbugs_total + housing_total + lead_paint_total
    
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
        "lead_paint_violations": lead_paint,
        "lead_paint_violations_total_count": lead_paint_total,
        "api_status": "partial" if total_records == 0 else "ok"
    }
    
    if total_records == 0:
        logger.warning(f"No data returned for {address}, {zip_code} - APIs may be down")
    
    return JsonResponse({"success": True, "data": result})